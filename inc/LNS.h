#pragma once
#include "BasicLNS.h"
#include "InitLNS.h"

//pibt related
#include "simplegrid.h"
#include "pibt_agent.h"
#include "problem.h"
#include "mapf.h"
#include "pibt.h"
#include "pps.h"
#include "winpibt.h"

enum destroy_heuristic { RANDOMAGENTS, RANDOMWALK, HOTSPOTS, DESTROY_COUNT };

class LNS : public BasicLNS
{
public:
    vector<Agent> agents;
    double preprocessing_time = 0;
    double initial_solution_runtime = 0;
    int initial_sum_of_costs = -1;
    int sum_of_costs_lowerbound = -1;
    int sum_of_distances = -1;
    int restart_times = 0;

    LNS(const Instance& instance, double time_limit,
        const string & init_algo_name, const string & replan_algo_name, const string & destroy_name,
        int neighbor_size, int num_of_iterations, bool init_lns, const string & init_destroy_name, bool use_sipp,
        int screen, PIBTPPS_option pipp_option, const string & bandit_algorithm_name, int neighborhoodSizes,double alphaUCB, double initialEpsilon, double lambdaDecay, double decayWindow);
    ~LNS()
    {
        delete init_lns;
    }
    bool getInitialSolution();
    bool run();
    void validateSolution() const;
    void writeIterStatsToFile(const string & file_name) const;
    void writeResultToFile(const string & file_name) const;
    void writePathsToFile(const string & file_name) const;
    string getSolverName() const override { return "LNS(" + init_algo_name + ";" + replan_algo_name + ")"; }
private:
    InitLNS* init_lns = nullptr;
    string init_algo_name;
    string replan_algo_name;
    bool use_init_lns; // use LNS to find initial solutions
    destroy_heuristic destroy_strategy = RANDOMAGENTS;
    int num_of_iterations;
    string init_destroy_name;
    PIBTPPS_option pipp_option;

    double initial_decayWindow; // New member variable
    bool initial_decayWindow_set = false;
    
    double temperature = 500;  // Temperature parameter for Boltzmann distribution
    
    // Add these new method declarations
    double calculatePathEntropy(const Agent& agent);
    double calculateLocationEntropy(int location, int timestep);
    std::vector<std::pair<int, double>> computeAgentEntropies();
   
    void randomWalkWithEntropy(int agent_id, int start_location, int start_timestep,
                              std::set<int>& conflicting_agents, int neighbor_size, 
                              int upperbound);

    PathTable path_table; // 1. stores the paths of all agents in a time-space table;
    // 2. avoid making copies of this variable as much as possible.
    unordered_set<int> tabu_list; // used by randomwalk strategy
    list<int> intersections;

    bool runEECBS();
    bool runCBS();
    bool runPP();
    bool runPIBT();
    bool runPPS();
    bool runWinPIBT();


    MAPF preparePIBTProblem(vector<int>& shuffled_agents);
    void updatePIBTResult(const PIBT_Agents& A, vector<int>& shuffled_agents);

    void chooseDestroyHeuristicbyALNS();

    bool generateNeighborByHotspots();
    bool generateNeighborBySynchroizedRandomWalk();

    int findMostDelayedAgent();
    int findRandomAgent() const;
    void randomWalk(int agent_id, int start_location, int start_timestep,
                    set<int>& neighbor, int neighbor_size, int upperbound);
    void synchronizedRandomWalk(const vector<int>& seed_agents, set<int>& conflicting_agents, int target_size);

};
