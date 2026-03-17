#include "LNS.h"
#include "ECBS.h"
#include <queue>
#include <algorithm> 
#include <numeric>   
#include <cmath>  
#include <random>   
#include <set>    
#include <unordered_map>
#include <vector>
#include <tuple>
#include <iostream>
#include <fstream>

LNS::LNS(const Instance& instance, double time_limit, const string & init_algo_name, const string & replan_algo_name,
         const string & destroy_name, int neighbor_size, int num_of_iterations, bool use_init_lns,
         const string & init_destroy_name, bool use_sipp, int screen, PIBTPPS_option pipp_option, const string & bandit_algorithm_name, int neighborhoodSizes,double alphaUCB, double initialEpsilon, double lambdaDecay, double decayWindow) :
         BasicLNS(instance, time_limit, neighbor_size, screen, bandit_algorithm_name, neighborhoodSizes, alphaUCB, initialEpsilon, lambdaDecay, decayWindow,DESTROY_COUNT),
         init_algo_name(init_algo_name),  replan_algo_name(replan_algo_name), num_of_iterations(num_of_iterations),
         use_init_lns(use_init_lns),init_destroy_name(init_destroy_name),
         path_table(instance.map_size), pipp_option(pipp_option)
{
    start_time = Time::now();
    replan_time_limit = time_limit / 100;
    // Set initial_decayWindow if not already set
    if (!initial_decayWindow_set) {
        initial_decayWindow = decayWindow;
        initial_decayWindow_set = true;
    }
    
    if (destroy_name == "Adaptive")
    {
        ALNS = true;
        heuristicBanditStats.destroy_weights.assign(DESTROY_COUNT, 1);
        heuristicBanditStats.destroy_weights_squared.assign(DESTROY_COUNT, 1);
        heuristicBanditStats.destroy_counts.assign(DESTROY_COUNT, 0);

        // Initialize recent_rewards for AlphaUCB and EpsilonGreedy
        heuristicBanditStats.recent_rewards.resize(DESTROY_COUNT);
        for (int i = 0; i < DESTROY_COUNT; ++i) {
            heuristicBanditStats.recent_rewards[i].resize(decayWindow);
        }
        decay_factor = 0;
        reaction_factor = 0;
        if(numberOfNeighborhoodSizeCandidates > 0)
        {
            for(int index = 0; index < DESTROY_COUNT; index++)
            {
                neighborhoodBanditStats.push_back(new BanditStats());
                neighborhoodBanditStats[index]->destroy_weights.assign(numberOfNeighborhoodSizeCandidates, 1);
                neighborhoodBanditStats[index]->destroy_weights_squared.assign(numberOfNeighborhoodSizeCandidates, 1);
                neighborhoodBanditStats[index]->destroy_counts.assign(numberOfNeighborhoodSizeCandidates, 0);
                
            }
        }
    }
    else if (destroy_name == "RandomWalk")
        destroy_strategy = RANDOMWALK;
    else if (destroy_name == "Hotspots")
        destroy_strategy = HOTSPOTS;
    else if (destroy_name == "Random")
        destroy_strategy = RANDOMAGENTS;
    else
    {
        cerr << "Destroy heuristic " << destroy_name << " does not exists. " << endl;
        exit(-1);
    }

    int N = instance.getDefaultNumberOfAgents();
    agents.reserve(N);
    for (int i = 0; i < N; i++)
        agents.emplace_back(instance, i, use_sipp);
    preprocessing_time = ((fsec)(Time::now() - start_time)).count();
    if (screen >= 2)
        cout << "Pre-processing time = " << preprocessing_time << " seconds." << endl;
}

bool LNS::run()
{   
    // only for statistic analysis, and thus is not included in runtime
    sum_of_distances = 0;
    for (const auto & agent : agents)
    {   
        
        sum_of_distances += agent.path_planner->my_heuristic[agent.path_planner->start_location];
    }

    initial_solution_runtime = 0;
    start_time = Time::now();
    bool succ = getInitialSolution();
    initial_solution_runtime = ((fsec)(Time::now() - start_time)).count();
    if (!succ && initial_solution_runtime < time_limit)
    {
        if (use_init_lns)
        {
            init_lns = new InitLNS(instance, agents, time_limit - initial_solution_runtime,
                    replan_algo_name,init_destroy_name, neighbor_size, screen, bandit_algorithm_name, numberOfNeighborhoodSizeCandidates);
            succ = init_lns->run();
            if (succ) // accept new paths
            {
                path_table.reset();
                for (const auto & agent : agents)
                {
                    path_table.insertPath(agent.id, agent.path);
                }
                init_lns->clear();
                initial_sum_of_costs = init_lns->sum_of_costs;
                sum_of_costs = initial_sum_of_costs;
            }
            initial_solution_runtime = ((fsec)(Time::now() - start_time)).count();
        }
        else // use random restart
        {
            while (!succ && initial_solution_runtime < time_limit)
            {
                succ = getInitialSolution();
                initial_solution_runtime = ((fsec)(Time::now() - start_time)).count();
                restart_times++;
            }
        }
    }

    int searchSuccess = succ? 1 : 0;
    iteration_stats.emplace_back(neighbor.agents.size(),
                                 initial_sum_of_costs, initial_solution_runtime, init_algo_name, 0, 0, searchSuccess);
    runtime = initial_solution_runtime;
    if (succ)
    {
        if (screen >= 1)
            cout << "Initial solution cost = " << initial_sum_of_costs << ", "
                 << "runtime = " << initial_solution_runtime << endl;
    }
    else
    {
        cout << "Failed to find an initial solution in "
             << runtime << " seconds after  " << restart_times << " restarts" << endl;
        return false; // terminate because no initial solution is found
    }

    while (runtime < time_limit && iteration_stats.size() <= num_of_iterations)
    {
        runtime =((fsec)(Time::now() - start_time)).count();
        if(screen >= 1)
            validateSolution();
        if (ALNS)
        {
            chooseDestroyHeuristicbyALNS();
        }

        switch (destroy_strategy)
        {
            case RANDOMWALK:
                succ = generateNeighborBySynchroizedRandomWalk();
                break;
            case HOTSPOTS:
                succ = generateNeighborByHotspots();
                break;
            case RANDOMAGENTS:
                neighbor.agents.resize(agents.size());
                for (int i = 0; i < (int)agents.size(); i++)
                    neighbor.agents[i] = i;
                if (neighbor.agents.size() > neighbor_size)
                {
                    std::random_shuffle(neighbor.agents.begin(), neighbor.agents.end());
                    neighbor.agents.resize(neighbor_size);
                }
                assert(neighbor.agents.size() > 0);
                succ = true;
                break;
            default:
                cerr << "Wrong neighbor generation strategy" << endl;
                exit(-1);
        }
        searchSuccess = succ? 1 : 0;
        if(!succ)
            continue;

        // store the neighbor information
        neighbor.old_paths.resize(neighbor.agents.size());
        neighbor.old_sum_of_costs = 0;
        for (int i = 0; i < (int)neighbor.agents.size(); i++)
        {
            if (replan_algo_name == "PP")
                neighbor.old_paths[i] = agents[neighbor.agents[i]].path;
            path_table.deletePath(neighbor.agents[i], agents[neighbor.agents[i]].path);
            neighbor.old_sum_of_costs += agents[neighbor.agents[i]].path.size() - 1;
        }

        if (replan_algo_name == "EECBS")
            succ = runEECBS();
        else if (replan_algo_name == "CBS")
            succ = runCBS();
        else if (replan_algo_name == "PP")
            succ = runPP();
        else
        {
            cerr << "Wrong replanning strategy" << endl;
            exit(-1);
        }

        if (ALNS) // update destroy heuristics
        {
            const bool condition = neighbor.old_sum_of_costs > neighbor.sum_of_costs;
            double value = (neighbor.old_sum_of_costs - neighbor.sum_of_costs);//
            if(neighbor.agents.size())
            {
                value /= neighbor.agents.size();
            }
            // Log per-iteration reward per heuristic for non-stationarity analysis
            {
                static std::ofstream reward_log;
                static bool header_written = false;
                if (!reward_log.is_open())
                    reward_log.open("reward_log.csv");
                if (!header_written)
                {
                    reward_log << "iteration,heuristic,reward\n";
                    header_written = true;
                }
                const char* heuristic_names[] = {"H_sync", "H_entr", "H_rand"};
                int h_idx = heuristicBanditStats.banditIndex;
                reward_log << iteration_stats.size() << ","
                           << (h_idx >= 0 && h_idx < 3 ? heuristic_names[h_idx] : "unknown") << ","
                           << value << "\n";
            }
            updateDestroyAndNeighborhoodWeights(value, condition);
        }
        runtime = ((fsec)(Time::now() - start_time)).count();
        sum_of_costs += neighbor.sum_of_costs - neighbor.old_sum_of_costs;
        if (screen >= 1)
            cout << "Iteration " << iteration_stats.size() << ", "
                 << "group size = " << neighbor.agents.size() << ", "
                 << "solution cost = " << sum_of_costs << ", "
                 << "remaining time = " << time_limit - runtime << endl;
        iteration_stats.emplace_back(neighbor.agents.size(), sum_of_costs, runtime, replan_algo_name, 0, 0, searchSuccess);
    }


    average_group_size = - iteration_stats.front().num_of_agents;
    for (const auto& data : iteration_stats)
        average_group_size += data.num_of_agents;
    if (average_group_size > 0)
        average_group_size /= (double)(iteration_stats.size() - 1);

    cout << getSolverName() << ": "
         << "runtime = " << runtime << ", "
         << "iterations = " << iteration_stats.size() << ", "
         << "solution cost = " << sum_of_costs << ", "
         << "initial solution cost = " << initial_sum_of_costs << ", "
         << "failed iterations = " << num_of_failures << endl;
    return true;
}


bool LNS::getInitialSolution()
{
    neighbor.agents.resize(agents.size());
    for (int i = 0; i < (int)agents.size(); i++)
        neighbor.agents[i] = i;
    neighbor.old_sum_of_costs = MAX_COST;
    neighbor.sum_of_costs = 0;
    bool succ = false;
    if (init_algo_name == "EECBS")
        succ = runEECBS();
    else if (init_algo_name == "PP")
        succ = runPP();
    else if (init_algo_name == "PIBT")
        succ = runPIBT();
    else if (init_algo_name == "PPS")
        succ = runPPS();
    else if (init_algo_name == "winPIBT")
        succ = runWinPIBT();
    else if (init_algo_name == "CBS")
        succ = runCBS();
    else
    {
        cerr <<  "Initial MAPF solver " << init_algo_name << " does not exist!" << endl;
        exit(-1);
    }
    if (succ)
    {
        initial_sum_of_costs = neighbor.sum_of_costs;
        sum_of_costs = neighbor.sum_of_costs;
        return true;
    }
    else
    {
        return false;
    }

}

bool LNS::runEECBS()
{
    vector<SingleAgentSolver*> search_engines;
    search_engines.reserve(neighbor.agents.size());
    for (int i : neighbor.agents)
    {
        search_engines.push_back(agents[i].path_planner);
    }

    ECBS ecbs(search_engines, screen - 1, &path_table);
    ecbs.setPrioritizeConflicts(true);
    ecbs.setDisjointSplitting(false);
    ecbs.setBypass(true);
    ecbs.setRectangleReasoning(true);
    ecbs.setCorridorReasoning(true);
    ecbs.setHeuristicType(heuristics_type::WDG, heuristics_type::GLOBAL);
    ecbs.setTargetReasoning(true);
    ecbs.setMutexReasoning(false);
    ecbs.setConflictSelectionRule(conflict_selection::EARLIEST);
    ecbs.setNodeSelectionRule(node_selection::NODE_CONFLICTPAIRS);
    ecbs.setSavingStats(false);
    double w;
    if (iteration_stats.empty())
        w = 5; // initial run
    else
        w = 1.1; // replan
    ecbs.setHighLevelSolver(high_level_solver_type::EES, w);
    runtime = ((fsec)(Time::now() - start_time)).count();
    double T = time_limit - runtime;
    if (!iteration_stats.empty()) // replan
        T = min(T, replan_time_limit);
    bool succ = ecbs.solve(T, 0);
    if (succ && ecbs.solution_cost < neighbor.old_sum_of_costs) // accept new paths
    {
        auto id = neighbor.agents.begin();
        for (size_t i = 0; i < neighbor.agents.size(); i++)
        {
            agents[*id].path = *ecbs.paths[i];
            path_table.insertPath(agents[*id].id, agents[*id].path);
            ++id;
        }
        neighbor.sum_of_costs = ecbs.solution_cost;
        if (sum_of_costs_lowerbound < 0)
            sum_of_costs_lowerbound = ecbs.getLowerBound();
    }
    else // stick to old paths
    {
        if (!neighbor.old_paths.empty())
        {
            for (int id : neighbor.agents)
            {
                path_table.insertPath(agents[id].id, agents[id].path);
            }
            neighbor.sum_of_costs = neighbor.old_sum_of_costs;
        }
        if (!succ)
            num_of_failures++;
    }
    return succ;
}
bool LNS::runCBS()
{
    if (screen >= 2)
        cout << "old sum of costs = " << neighbor.old_sum_of_costs << endl;
    vector<SingleAgentSolver*> search_engines;
    search_engines.reserve(neighbor.agents.size());
    for (int i : neighbor.agents)
    {
        search_engines.push_back(agents[i].path_planner);
    }

    CBS cbs(search_engines, screen - 1, &path_table);
    cbs.setPrioritizeConflicts(true);
    cbs.setDisjointSplitting(false);
    cbs.setBypass(true);
    cbs.setRectangleReasoning(true);
    cbs.setCorridorReasoning(true);
    cbs.setHeuristicType(heuristics_type::WDG, heuristics_type::ZERO);
    cbs.setTargetReasoning(true);
    cbs.setMutexReasoning(false);
    cbs.setConflictSelectionRule(conflict_selection::EARLIEST);
    cbs.setNodeSelectionRule(node_selection::NODE_CONFLICTPAIRS);
    cbs.setSavingStats(false);
    cbs.setHighLevelSolver(high_level_solver_type::ASTAR, 1);
    runtime = ((fsec)(Time::now() - start_time)).count();
    double T = time_limit - runtime; // time limit
    if (!iteration_stats.empty()) // replan
        T = min(T, replan_time_limit);
    bool succ = cbs.solve(T, 0);
    if (succ && cbs.solution_cost <= neighbor.old_sum_of_costs) // accept new paths
    {
        auto id = neighbor.agents.begin();
        for (size_t i = 0; i < neighbor.agents.size(); i++)
        {
            agents[*id].path = *cbs.paths[i];
            path_table.insertPath(agents[*id].id, agents[*id].path);
            ++id;
        }
        neighbor.sum_of_costs = cbs.solution_cost;
        if (sum_of_costs_lowerbound < 0)
            sum_of_costs_lowerbound = cbs.getLowerBound();
    }
    else // stick to old paths
    {
        if (!neighbor.old_paths.empty())
        {
            for (int id : neighbor.agents)
            {
                path_table.insertPath(agents[id].id, agents[id].path);
            }
            neighbor.sum_of_costs = neighbor.old_sum_of_costs;

        }
        if (!succ)
            num_of_failures++;
    }
    return succ;
}
bool LNS::runPP()
{
    auto shuffled_agents = neighbor.agents;
    std::random_shuffle(shuffled_agents.begin(), shuffled_agents.end());
    if (screen >= 2) {
        for (auto id : shuffled_agents)
            cout << id << "(" << agents[id].path_planner->my_heuristic[agents[id].path_planner->start_location] <<
                "->" << agents[id].path.size() - 1 << "), ";
        cout << endl;
    }
    int remaining_agents = (int)shuffled_agents.size();
    auto p = shuffled_agents.begin();
    neighbor.sum_of_costs = 0;
    runtime = ((fsec)(Time::now() - start_time)).count();
    double T = time_limit - runtime; // time limit
    if (!iteration_stats.empty()) // replan
        T = min(T, replan_time_limit);
    auto time = Time::now();
    ConstraintTable constraint_table(instance.num_of_cols, instance.map_size, &path_table);
    while (p != shuffled_agents.end() && ((fsec)(Time::now() - time)).count() < T)
    {
        int id = *p;
        if (screen >= 3)
            cout << "Remaining agents = " << remaining_agents <<
                 ", remaining time = " << T - ((fsec)(Time::now() - time)).count() << " seconds. " << endl
                 << "Agent " << agents[id].id << endl;
        agents[id].path = agents[id].path_planner->findPath(constraint_table);

        int path_collisions = agents[id].path_planner->num_collisions; 
        
        if (agents[id].path.empty()) break;
        neighbor.sum_of_costs += (int)agents[id].path.size() - 1;
        if (neighbor.sum_of_costs >= neighbor.old_sum_of_costs)
            break;
        remaining_agents--;
        path_table.insertPath(agents[id].id, agents[id].path);
        ++p;
    }
    if (remaining_agents == 0 && neighbor.sum_of_costs <= neighbor.old_sum_of_costs) // accept new paths
    {
        return true;
    }
    else // stick to old paths
    {
        if (p != shuffled_agents.end())
            num_of_failures++;
        auto p2 = shuffled_agents.begin();
        while (p2 != p)
        {
            int a = *p2;
            path_table.deletePath(agents[a].id, agents[a].path);
            ++p2;
        }
        if (!neighbor.old_paths.empty())
        {
            p2 = neighbor.agents.begin();
            for (int i = 0; i < (int)neighbor.agents.size(); i++)
            {
                int a = *p2;
                agents[a].path = neighbor.old_paths[i];
                path_table.insertPath(agents[a].id, agents[a].path);
                ++p2;
            }
            neighbor.sum_of_costs = neighbor.old_sum_of_costs;
        }
        return false;
    }
}
bool LNS::runPPS(){
    auto shuffled_agents = neighbor.agents;
    std::random_shuffle(shuffled_agents.begin(), shuffled_agents.end());

    MAPF P = preparePIBTProblem(shuffled_agents);
    P.setTimestepLimit(pipp_option.timestepLimit);

    // seed for solver
    auto* MT_S = new std::mt19937(0);
    PPS solver(&P,MT_S);
    solver.setTimeLimit(time_limit);
    bool result = solver.solve();
    if (result)
        updatePIBTResult(P.getA(),shuffled_agents);
    return result;
}
bool LNS::runPIBT(){
    auto shuffled_agents = neighbor.agents;
     std::random_shuffle(shuffled_agents.begin(), shuffled_agents.end());

    MAPF P = preparePIBTProblem(shuffled_agents);

    // seed for solver
    auto MT_S = new std::mt19937(0);
    PIBT solver(&P,MT_S);
    solver.setTimeLimit(time_limit);
    bool result = solver.solve();
    if (result)
        updatePIBTResult(P.getA(),shuffled_agents);
    return result;
}
bool LNS::runWinPIBT(){
    auto shuffled_agents = neighbor.agents;
    std::random_shuffle(shuffled_agents.begin(), shuffled_agents.end());

    MAPF P = preparePIBTProblem(shuffled_agents);
    P.setTimestepLimit(pipp_option.timestepLimit);

    // seed for solver
    auto MT_S = new std::mt19937(0);
    winPIBT solver(&P,pipp_option.windowSize,pipp_option.winPIBTSoft,MT_S);
    solver.setTimeLimit(time_limit);
    bool result = solver.solve();
    if (result)
        updatePIBTResult(P.getA(),shuffled_agents);
    return result;
}

MAPF LNS::preparePIBTProblem(vector<int>& shuffled_agents){

    // seed for problem and graph
    auto MT_PG = new std::mt19937(0);
    Graph* G = new SimpleGrid(instance.getMapFile());

    std::vector<Task*> T;
    PIBT_Agents A;

    for (int i : shuffled_agents){
        assert(G->existNode(agents[i].path_planner->start_location));
        assert(G->existNode(agents[i].path_planner->goal_location));
        auto a = new PIBT_Agent(G->getNode( agents[i].path_planner->start_location));
        A.push_back(a);
        Task* tau = new Task(G->getNode( agents[i].path_planner->goal_location));


        T.push_back(tau);
        if(screen>=5){
            cout<<"Agent "<<i<<" start: " <<a->getNode()->getPos()<<" goal: "<<tau->getG().front()->getPos()<<endl;
        }
    }

    return MAPF(G, A, T, MT_PG);

}

void LNS::updatePIBTResult(const PIBT_Agents& A, vector<int>& shuffled_agents){
    int soc = 0;
    for (int i=0; i<A.size();i++){
        int a_id = shuffled_agents[i];

        agents[a_id].path.resize(A[i]->getHist().size());
        int last_goal_visit = 0;
        if(screen>=2)
            std::cout<<A[i]->logStr()<<std::endl;
        for (int n_index = 0; n_index < A[i]->getHist().size(); n_index++){
            auto n = A[i]->getHist()[n_index];
            agents[a_id].path[n_index] = PathEntry(n->v->getId());

            //record the last time agent reach the goal from a non-goal vertex.
            if(agents[a_id].path_planner->goal_location == n->v->getId()
                && n_index - 1>=0
                && agents[a_id].path_planner->goal_location !=  agents[a_id].path[n_index - 1].location)
                last_goal_visit = n_index;

        }
        //resize to last goal visit time
        agents[a_id].path.resize(last_goal_visit + 1);
        if(screen>=2)
            std::cout<<" Length: "<< agents[a_id].path.size() <<std::endl;
        if(screen>=5){
            cout <<"Agent "<<a_id<<":";
            for (auto loc : agents[a_id].path){
                cout <<loc.location<<",";
            }
            cout<<endl;
        }
        path_table.insertPath(agents[a_id].id, agents[a_id].path);
        soc += (int)agents[a_id].path.size()-1;
    }

    neighbor.sum_of_costs =soc;
}

void LNS::chooseDestroyHeuristicbyALNS()
{
    sampleDestroyHeuristicAndNeighborhoodSize();
    switch (selected_neighbor)
    {
        case 0 : destroy_strategy = RANDOMWALK; break;
        case 1 : destroy_strategy = HOTSPOTS; break;
        case 2 : destroy_strategy = RANDOMAGENTS; break;
        default : cerr << "ERROR" << endl; exit(-1);
    }
    
}


bool LNS::generateNeighborBySynchroizedRandomWalk()
{
    if (neighbor_size >= (int)agents.size())
    {
        neighbor.agents.resize(agents.size());
        for (int i = 0; i < (int)agents.size(); i++)
            neighbor.agents[i] = i;
        return true;
    }

    // Start with multiple seed agents - select top k most delayed agents
    vector<pair<int, int>> delayed_agents; // (delays, agent_id)
    for (int i = 0; i < (int)agents.size(); i++)
    {
        if (tabu_list.find(i) != tabu_list.end())
            continue;
        delayed_agents.emplace_back(agents[i].getNumOfDelays(), i);
    }

    // Sort by delays in descending order
    sort(delayed_agents.begin(), delayed_agents.end(),
         [](const auto& a, const auto& b) { return a.first > b.first; });

    // Select top k agents as seeds (k = min(3, neighbor_size/2))
  
    int num_seeds = 1 + std::rand() % (neighbor_size / 3);
    set<int> neighbors_set;
    vector<int> seed_agents;

    for (int i = 0; i < num_seeds && i < (int)delayed_agents.size(); i++)
    {
        if (delayed_agents[i].first > 0) // only include if they have delays
        {
            seed_agents.push_back(delayed_agents[i].second);
            neighbors_set.insert(delayed_agents[i].second);
            tabu_list.insert(delayed_agents[i].second);
        }
    }

    if (seed_agents.empty())
    {
        tabu_list.clear();
        return false;
    }

    // Perform synchronized random walks from all seed agents
    synchronizedRandomWalk(seed_agents, neighbors_set, neighbor_size);

    // If we still need more agents, perform additional walks
    //int attempts = 0;
    //while (neighbors_set.size() < neighbor_size && attempts < 10)
    //{
    //    cout << "Attempting to find more agents by random walk..." << endl;
        // Select random agents from current set as new seeds
    //    vector<int> new_seeds;
    //    vector<int> current_agents(neighbors_set.begin(), neighbors_set.end());
    //    for (int i = 0; i < min(2, (int)current_agents.size()); i++)
    //    {
    //        int idx = rand() % current_agents.size();
    //        new_seeds.push_back(current_agents[idx]);
    //    }
        
    //    synchronizedRandomWalk(new_seeds, neighbors_set, neighbor_size);
    //    attempts++;
    //}

    if (neighbors_set.size() < 2)
        return false;

    neighbor.agents.assign(neighbors_set.begin(), neighbors_set.end());
    
    if (screen >= 2)
    {
        cout << "Generate " << neighbor.agents.size() << " neighbors by synchronized random walks from "
             << seed_agents.size() << " seed agents" << endl;
    }
    
    return true;
}

void LNS::synchronizedRandomWalk(const vector<int>& seed_agents, set<int>& conflicting_agents, int target_size)
{
    vector<pair<int, int>> current_states;
    vector<int> upperbounds;
    
    // Initialize states and upperbounds
    for (int agent_id : seed_agents)
    {
        current_states.emplace_back(agents[agent_id].path[0].location, 0);
        upperbounds.push_back((int)agents[agent_id].path.size() - 1);
    }

    // Simply use number of agents as the step limit
    int max_steps = agents.size();  
    // Track progress
    int steps_since_last_find = 0;
    const int MAX_STEPS_WITHOUT_IMPROVEMENT = max_steps/2; // Adjust early stopping based on num agents

    // Perform synchronized random walks
    for (int step = 0; step < max_steps && conflicting_agents.size() < target_size; step++)
    {
        int previous_size = conflicting_agents.size();

        // For each seed agent
        for (size_t i = 0; i < seed_agents.size(); i++)
        {
            int agent_id = seed_agents[i];
            int cur_loc = current_states[i].first;
            int cur_time = current_states[i].second;

            if (cur_time >= upperbounds[i])
                continue;

            // Get possible next locations
            auto next_locs = instance.getNeighbors(cur_loc);
            next_locs.push_back(cur_loc); // Include staying in place

            // Try each possible move
            while (!next_locs.empty() && conflicting_agents.size() < target_size)
            {
                int idx = rand() % next_locs.size();
                auto it = next_locs.begin();
                advance(it, idx);
                int next_loc = *it;

                // Check if this move is valid
                int next_h_val = agents[agent_id].path_planner->my_heuristic[next_loc];
                if (cur_time + 1 + next_h_val < upperbounds[i])
                {
                    // Check for conflicts with this move
                    path_table.getConflictingAgents(agent_id, conflicting_agents, 
                                                  cur_loc, next_loc, cur_time + 1);

                    // Update position
                    current_states[i].first = next_loc;
                    current_states[i].second = cur_time + 1;
                    break;
                }
                next_locs.erase(it);
            }
        }

        // Check if we found any new conflicts
        if (conflicting_agents.size() > previous_size)
        {
            steps_since_last_find = 0;
        }
        else
        {
            steps_since_last_find++;
            
            // Random jumps if stuck
            if (steps_since_last_find >= MAX_STEPS_WITHOUT_IMPROVEMENT / 2)
            {
                for (size_t i = 0; i < seed_agents.size(); i++)
                {
                    if (upperbounds[i] > 1)
                    {
                        int new_time = rand() % upperbounds[i];
                        current_states[i] = make_pair(
                            agents[seed_agents[i]].path[new_time].location, 
                            new_time
                        );
                    }
                }
            }
            
            if (steps_since_last_find >= MAX_STEPS_WITHOUT_IMPROVEMENT)
            {
                break;
            }
        }
    }
}



// Add these implementations to your existing LNS.cpp file

double LNS::calculatePathEntropy(const Agent& agent) {
    unordered_map<int, int> location_frequencies;
    location_frequencies.reserve(agent.path.size());

    for (const auto& node : agent.path)
        location_frequencies[node.location]++;

    double path_length = static_cast<double>(agent.path.size());
    double entropy = 0.0;
    for (const auto& freq_pair : location_frequencies) {
        double probability = freq_pair.second / path_length;
        entropy -= probability * log2(probability);
    }
    return entropy;
}

double LNS::calculateLocationEntropy(int location, int timestep) {
    // Each agent either is or isn't at this location → each contributes probability 1/n,
    // so Shannon entropy = log2(n). No map allocation needed.
    int count = 0;
    for (size_t i = 0; i < agents.size(); i++) {
        if (timestep < (int)agents[i].path.size() &&
            agents[i].path[timestep].location == location)
            ++count;
    }
    return count > 1 ? log2((double)count) : 0.0;
}

vector<pair<int, double>> LNS::computeAgentEntropies() {
    vector<pair<int, double>> agent_entropies;
    agent_entropies.reserve(agents.size());
    
    for (size_t i = 0; i < agents.size(); i++) {
        if (tabu_list.find(i) != tabu_list.end()) continue;
        
        double path_entropy = calculatePathEntropy(agents[i]);
        double delay_factor = agents[i].getNumOfDelays();
        
        // Combine entropy with delay information
        double combined_score = path_entropy * (1.0 + delay_factor);
        agent_entropies.push_back(make_pair((int)i, combined_score));
    }
    
    // Sort by entropy score in descending order
    sort(agent_entropies.begin(), agent_entropies.end(),
         [](const auto& a, const auto& b) { return a.second > b.second; });
    
    return agent_entropies;
}

bool LNS::generateNeighborByHotspots() {
    if (neighbor_size >= (int)agents.size()) {
        neighbor.agents.resize(agents.size());
        for (int i = 0; i < (int)agents.size(); i++)
            neighbor.agents[i] = i;
        return true;
    }

    auto agent_entropies = computeAgentEntropies();
    if (agent_entropies.empty()) return false;

    set<int> selected_agents;
    vector<double> probabilities;
    double sum_exp = 0.0;

    // Boltzmann sampling
    for (const auto& agent_entry : agent_entropies) {
        double exp_val = exp(agent_entry.second / temperature);
        probabilities.push_back(exp_val);
        sum_exp += exp_val;
    }

    // Normalize probabilities
    for (double& prob : probabilities) {
        prob /= sum_exp;
    }

    // Select initial agent
    double rand_val = static_cast<double>(rand()) / RAND_MAX;
    double cumulative_prob = 0.0;
    int selected_idx = 0;

    for (size_t i = 0; i < probabilities.size(); i++) {
        cumulative_prob += probabilities[i];
        if (rand_val <= cumulative_prob) {
            selected_idx = (int)i;
            break;
        }
    }
    
    int initial_agent = agent_entropies[selected_idx].first;
    selected_agents.insert(initial_agent);

    // Start walk from the most congested location on the agent's path
    // (argmax location entropy) rather than path[0] which is typically empty.
    const auto& apath = agents[initial_agent].path;
    int upperbound    = (int)apath.size() - 1;
    int best_start_loc = apath[0].location;
    int best_start_t   = 0;
    double best_ent    = -1.0;
    for (int t = 0; t < upperbound; t++) {
        double ent = calculateLocationEntropy(apath[t].location, t);
        if (ent > best_ent) { best_ent = ent; best_start_loc = apath[t].location; best_start_t = t; }
    }

    randomWalkWithEntropy(initial_agent, best_start_loc,
                         best_start_t, selected_agents, neighbor_size,
                         upperbound);

    if (selected_agents.size() < 2)
        return false;

    neighbor.agents.assign(selected_agents.begin(), selected_agents.end());
    
    if (screen >= 2) {
        cout << "Generate " << neighbor.agents.size() 
             << " neighbors by entropy-based selection. Initial agent: " 
             << initial_agent << " (entropy: " 
             << agent_entropies[selected_idx].second << ")" << endl;
    }
    
    return true;
}

void LNS::randomWalkWithEntropy(int agent_id, int start_location, int start_timestep,
                               set<int>& conflicting_agents, int neighbor_size, 
                               int upperbound) {
    int loc = start_location;
    
    for (int t = start_timestep; t < upperbound; t++) {
        auto next_locs = instance.getNeighbors(loc);
        next_locs.push_back(loc);
        
        vector<pair<int, double>> location_scores;
        for (int next_loc : next_locs) {
            double entropy = calculateLocationEntropy(next_loc, t + 1);
            double h_val = agents[agent_id].path_planner->my_heuristic[next_loc];
            double score = entropy * (1.0 / (1.0 + h_val));
            location_scores.push_back(make_pair(next_loc, score));
        }
        
        sort(location_scores.begin(), location_scores.end(),
             [](const auto& a, const auto& b) { return a.second > b.second; });
        
        bool moved = false;
        for (const auto& loc_score : location_scores) {
            int next_loc = loc_score.first;
            int next_h_val = agents[agent_id].path_planner->my_heuristic[next_loc];
            
            if (t + 1 + next_h_val < upperbound) {
                path_table.getConflictingAgents(agent_id, conflicting_agents, 
                                              loc, next_loc, t + 1);
                // Truncate to neighbor_size if a single call overshoots
                while ((int)conflicting_agents.size() > neighbor_size)
                {
                    auto it = conflicting_agents.end();
                    --it;
                    conflicting_agents.erase(it);
                }
                loc = next_loc;
                moved = true;
                break;
            }
        }
        
        if (!moved || conflicting_agents.size() >= neighbor_size)
            break;
    }
}




int LNS::findMostDelayedAgent()
{
    int a = -1;
    int max_delays = -1;
    for (int i = 0; i < agents.size(); i++)
    {
        if (tabu_list.find(i) != tabu_list.end())
            continue;
        int delays = agents[i].getNumOfDelays();
        if (max_delays < delays)
        {
            a = i;
            max_delays = delays;
        }
    }
    if (max_delays == 0)
    {
        tabu_list.clear();
        return -1;
    }
    tabu_list.insert(a);
    if (tabu_list.size() == agents.size())
        tabu_list.clear();
    return a;
}

void LNS::validateSolution() const
{
    int sum = 0;
    for (const auto& a1_ : agents)
    {
        if (a1_.path.empty())
        {
            cerr << "No solution for agent " << a1_.id << endl;
            exit(-1);
        }
        else if (a1_.path_planner->start_location != a1_.path.front().location)
        {
            cerr << "The path of agent " << a1_.id << " starts from location " << a1_.path.front().location
                << ", which is different from its start location " << a1_.path_planner->start_location << endl;
            exit(-1);
        }
        else if (a1_.path_planner->goal_location != a1_.path.back().location)
        {
            cerr << "The path of agent " << a1_.id << " ends at location " << a1_.path.back().location
                 << ", which is different from its goal location " << a1_.path_planner->goal_location << endl;
            exit(-1);
        }
        for (int t = 1; t < (int) a1_.path.size(); t++ )
        {
            if (!instance.validMove(a1_.path[t - 1].location, a1_.path[t].location))
            {
                cerr << "The path of agent " << a1_.id << " jump from "
                     << a1_.path[t - 1].location << " to " << a1_.path[t].location
                     << " between timesteps " << t - 1 << " and " << t << endl;
                exit(-1);
            }
        }
        sum += (int) a1_.path.size() - 1;
        for (const auto  & a2_: agents)
        {
            if (a1_.id >= a2_.id || a2_.path.empty())
                continue;
            const auto & a1 = a1_.path.size() <= a2_.path.size()? a1_ : a2_;
            const auto & a2 = a1_.path.size() <= a2_.path.size()? a2_ : a1_;
            int t = 1;
            for (; t < (int) a1.path.size(); t++)
            {
                if (a1.path[t].location == a2.path[t].location) // vertex conflict
                {
                    cerr << "Find a vertex conflict between agents " << a1.id << " and " << a2.id <<
                            " at location " << a1.path[t].location << " at timestep " << t << endl;
                    exit(-1);
                }
                else if (a1.path[t].location == a2.path[t - 1].location &&
                        a1.path[t - 1].location == a2.path[t].location) // edge conflict
                {
                    cerr << "Find an edge conflict between agents " << a1.id << " and " << a2.id <<
                         " at edge (" << a1.path[t - 1].location << "," << a1.path[t].location <<
                         ") at timestep " << t << endl;
                    exit(-1);
                }
            }
            int target = a1.path.back().location;
            for (; t < (int) a2.path.size(); t++)
            {
                if (a2.path[t].location == target)  // target conflict
                {
                    cerr << "Find a target conflict where agent " << a2.id << " (of length " << a2.path.size() - 1<<
                         ") traverses agent " << a1.id << " (of length " << a1.path.size() - 1<<
                         ")'s target location " << target << " at timestep " << t << endl;
                    exit(-1);
                }
            }
        }
    }
    if (sum_of_costs != sum)
    {
        cerr << "The computed sum of costs " << sum_of_costs <<
             " is different from the sum of the paths in the solution " << sum << endl;
        exit(-1);
    }
}

void LNS::writeIterStatsToFile(const string & file_name) const
{
    if (init_lns != nullptr)
    {
        init_lns->writeIterStatsToFile(file_name + "-initLNS.csv");
    }
    if (iteration_stats.size() <= 1)
        return;
    string name = file_name;
    if (use_init_lns or num_of_iterations > 0)
        name += "-LNS.csv";
    else
        name += "-" + init_algo_name + ".csv";
    std::ofstream output;
    output.open(name);
    // header
    output << "num of agents," <<
           "sum of costs," <<
           "runtime," <<
           "cost lowerbound," <<
           "sum of distances," <<
           "MAPF algorithm" << endl;

    for (const auto &data : iteration_stats)
    {
        output << data.num_of_agents << "," <<
               data.sum_of_costs << "," <<
               data.runtime << "," <<
               max(sum_of_costs_lowerbound, sum_of_distances) << "," <<
               sum_of_distances << "," <<
               data.algorithm << endl;
    }
    output.close();
}

void LNS::writeResultToFile(const string & file_name) const
{
    if (init_lns != nullptr)
    {
        init_lns->writeResultToFile(file_name + "-initLNS.csv", sum_of_distances, preprocessing_time);
    }
    string name = file_name;
    if (use_init_lns or num_of_iterations > 0)
        name += "-LNS.csv";
    else
        name += "-" + init_algo_name + ".csv";
    std::ifstream infile(name);
    bool exist = infile.good();
    infile.close();
    if (!exist)
    {
        ofstream addHeads(name);
        addHeads << "number of agents,runtime,solution cost,initial solution cost,lower bound,sum of distance," <<
                 "iterations," <<
                 "group size," <<
                 "runtime of initial solution,restart times,area under curve," <<
                 "LL expanded nodes,LL generated,LL reopened,LL runs," <<
                 "preprocessing runtime,solver name,instance name,success,selected_neighbor,neighbor_size" << endl;
        addHeads.close();
    }
    uint64_t num_LL_expanded = 0, num_LL_generated = 0, num_LL_reopened = 0, num_LL_runs = 0;
    for (auto & agent : agents)
    {
        agent.path_planner->reset();
        num_LL_expanded += agent.path_planner->accumulated_num_expanded;
        num_LL_generated += agent.path_planner->accumulated_num_generated;
        num_LL_reopened += agent.path_planner->accumulated_num_reopened;
        num_LL_runs += agent.path_planner->num_runs;
    }
    double auc = 0;
    if (!iteration_stats.empty())
    {
        auto prev = iteration_stats.begin();
        auto curr = prev;
        ++curr;
        while (curr != iteration_stats.end() && curr->runtime < time_limit)
        {
            auc += (prev->sum_of_costs - sum_of_distances) * (curr->runtime - prev->runtime);
            prev = curr;
            ++curr;
        }
        auc += (prev->sum_of_costs - sum_of_distances) * (time_limit - prev->runtime);
    }
    ofstream stats(name, std::ios::app);
    stats << agents.size() << "," << runtime << "," << sum_of_costs << "," << initial_sum_of_costs << "," <<
          max(sum_of_distances, sum_of_costs_lowerbound) << "," << sum_of_distances << "," <<
          iteration_stats.size() << "," << average_group_size << "," <<
          initial_solution_runtime << "," << restart_times << "," << auc << "," <<
          num_LL_expanded << "," << num_LL_generated << "," << num_LL_reopened << "," << num_LL_runs << "," <<
          preprocessing_time << "," << getSolverName() << "," << instance.getInstanceName() << "," << iteration_stats.back().success << "," << selected_neighbor << "," << neighbor_size << endl;
    stats.close();
}

void LNS::writePathsToFile(const string & file_name) const
{
    std::ofstream output;
    output.open(file_name);

    for (const auto &agent : agents)
    {
        output << "Agent " << agent.id << ":";
        for (const auto &state : agent.path)
            output << "(" << instance.getRowCoordinate(state.location) << "," <<
                            instance.getColCoordinate(state.location) << ")->";
        output << endl;
    }
    output.close();
}
