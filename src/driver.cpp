#include <boost/program_options.hpp>
#include <boost/tokenizer.hpp>
#include "LNS.h"
#include "AnytimeBCBS.h"
#include "AnytimeEECBS.h"
#include "PIBT/pibt.h"
#include <unordered_set>

/* Main function */
int main(int argc, char** argv)
{
	namespace po = boost::program_options;
	// Declare the supported options.
	po::options_description desc("Allowed options");
	desc.add_options()
		("help", "produce help message")
		("map,m", po::value<std::string>()->required(), "input file for map")
		("agents,a", po::value<std::string>()->required(), "input file for agents")
		("agentNum,k", po::value<int>()->default_value(0), "number of agents")
        ("output,o", po::value<std::string>(), "output file name (no extension)")
        ("outputPaths", po::value<std::string>(), "output file for paths")
        ("cutoffTime,t", po::value<double>()->default_value(7200), "cutoff time (seconds)")
		("screen,s", po::value<int>()->default_value(1),
		        "screen option (0: none; 1: LNS results; 2:LNS detailed results; 3:MAPF detailed results)")
		("stats", po::value<std::string>(), "output stats file")
        ("banditAlgo", po::value<std::string>()->default_value("AlphaUCB"), "Bandit algorithm for Adaptive LNS (Random, Roulette, UCB1, AlphaUCB, EpsilonGreedy,Thompson)")

		// solver
		("solver", po::value<std::string>()->default_value("LNS"), "solver (LNS, A-BCBS, A-EECBS)")
		("sipp", po::value<bool>()->default_value(true), "Use SIPP as the single-agent solver")
		("seed", po::value<int>()->default_value(0), "Random seed")

        // params for LNS
        ("initLNS", po::value<bool>()->default_value(true),
             "use LNS to find initial solutions if the initial solver fails")
        ("neighborSize", po::value<int>()->default_value(8), "Size of the neighborhood")
        ("neighborCandidateSizes", po::value<int>()->default_value(1), "Number of possible neighborhood sizes (bandit adaptation)")
        ("maxIterations", po::value<int>()->default_value(100000000), "maximum number of iterations")
        ("alphaUCB", po::value<double>()->default_value(10000), "parameter alpha of UCB")
        ("initialEpsilon", po::value<double>()->default_value(0.5), "Initial epsilon greedy")
        ("lambdaDecay", po::value<double>()->default_value(5), "lambda decay for epsilon greedy")
        ("decayWindow", po::value<double>()->default_value(100), "sliding window for non stationary environment")
        ("initAlgo", po::value<std::string>()->default_value("PP"),
                "MAPF algorithm for finding the initial solution (EECBS, PP, PPS, CBS, PIBT, winPIBT)")
        ("replanAlgo", po::value<std::string>()->default_value("PP"),
                "MAPF algorithm for replanning (EECBS, CBS, PP)")
        ("destroyStrategy", po::value<std::string>()->default_value("Adaptive"),
                "Heuristics for finding subgroups (Random, RandomWalk, Hotspots, Adaptive)")
        ("pibtWindow", po::value<int>()->default_value(5),
             "window size for winPIBT")
        ("winPibtSoftmode", po::value<bool>()->default_value(true),
             "winPIBT soft mode")

         // params for initLNS
         ("initDestroyStrategy", po::value<std::string>()->default_value("Adaptive"),
          "Heuristics for finding subgroups (Target, Collision, Random, Adaptive)")
		;

	po::variables_map vm;
	po::store(po::parse_command_line(argc, argv, desc), vm);

	if (vm.count("help")) {
		std::cout << desc << std::endl;
		return 1;
	}
	po::notify(vm);

	// Validate banditAlgo
	std::unordered_set<std::string> valid_bandit_algos = {
	    "Random", "Roulette", "UCB1", "AlphaUCB", "EpsilonGreedy", "Thompson"
	};
	std::string bandit_algo = vm["banditAlgo"].as<std::string>();
	if (valid_bandit_algos.find(bandit_algo) == valid_bandit_algos.end()) {
	    std::cerr << "Invalid bandit algorithm: " << bandit_algo << std::endl;
	    return -1;
	}

	PIBTPPS_option pipp_option;
	pipp_option.windowSize = vm["pibtWindow"].as<int>();
	pipp_option.winPIBTSoft = vm["winPibtSoftmode"].as<bool>();

	srand(static_cast<int>(time(0)));

	Instance instance(vm["map"].as<std::string>(), vm["agents"].as<std::string>(), vm["agentNum"].as<int>());
	double time_limit = vm["cutoffTime"].as<double>();
	int screen = vm["screen"].as<int>();
	srand(vm["seed"].as<int>());

	if (vm["solver"].as<std::string>() == "LNS")
	{
	    LNS lns(instance, time_limit,
	            vm["initAlgo"].as<std::string>(),
	            vm["replanAlgo"].as<std::string>(),
	            vm["destroyStrategy"].as<std::string>(),
	            vm["neighborSize"].as<int>(),
	            vm["maxIterations"].as<int>(),
	            vm["initLNS"].as<bool>(),
	            vm["initDestroyStrategy"].as<std::string>(),
	            vm["sipp"].as<bool>(),
	            screen, pipp_option, vm["banditAlgo"].as<std::string>(),
	            vm["neighborCandidateSizes"].as<int>(),
	            vm["alphaUCB"].as<double>(),  
	            vm["initialEpsilon"].as<double>(),
	            vm["lambdaDecay"].as<double>(),
	            vm["decayWindow"].as<double>());
	    bool succ = lns.run();
	    if (succ)
	    {
	        lns.validateSolution();
	        if (vm.count("outputPaths"))
	            lns.writePathsToFile(vm["outputPaths"].as<std::string>());
	    }
	    if (vm.count("output"))
	        lns.writeResultToFile(vm["output"].as<std::string>());
	    if (vm.count("stats"))
	        lns.writeIterStatsToFile(vm["stats"].as<std::string>());
	}
	else if (vm["solver"].as<std::string>() == "A-BCBS") // anytime BCBS(w, 1)
	{
	    AnytimeBCBS bcbs(instance, time_limit, screen);
	    bcbs.run();
	    bcbs.validateSolution();
	    if (vm.count("output"))
	        bcbs.writeResultToFile(vm["output"].as<std::string>() + ".csv");
	    if (vm.count("stats"))
	        bcbs.writeIterStatsToFile(vm["stats"].as<std::string>());
	}
	else if (vm["solver"].as<std::string>() == "A-EECBS") // anytime EECBS
	{
	    AnytimeEECBS eecbs(instance, time_limit, screen);
	    eecbs.run();
	    eecbs.validateSolution();
	    if (vm.count("output"))
	        eecbs.writeResultToFile(vm["output"].as<std::string>() + ".csv");
	    if (vm.count("stats"))
	        eecbs.writeIterStatsToFile(vm["stats"].as<std::string>());
	}
	else
	{
	    std::cerr << "Solver " << vm["solver"].as<std::string>() << " does not exist!" << std::endl;
	    exit(-1);
	}
	return 0;
}
