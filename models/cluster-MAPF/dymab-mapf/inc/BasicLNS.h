#pragma once
#include <deque>
#include "common.h"
#include "SpaceTimeAStar.h"
#include "SIPP.h"
#include <random>

#define NEIGHBOR_SIZE_OPTIONS1 1
#define NEIGHBOR_SIZE_OPTIONS3 3
#define NEIGHBOR_SIZE_OPTIONS5 5
#define NEIGHBOR_SIZE_OPTIONS7 7
#define NEIGHBOR_SIZE_OPTIONS9 9

enum bandit_type { RANDOM_BANDIT, ROULETTE_WHEEL, EpsilonGreedy, UCB1, THOMPSON_SAMPLING, AlphaUCB};

struct Agent
{
    int id;
    SingleAgentSolver* path_planner = nullptr; // start, goal, and heuristics are stored in the path planner
    Path path;

    Agent(const Instance& instance, int id, bool sipp) : id(id)
    {
        if(sipp)
            path_planner = new SIPP(instance, id);
        else
            path_planner = new SpaceTimeAStar(instance, id);
    }
    ~Agent(){ delete path_planner; }

    int getNumOfDelays() const
    {
        return (int) path.size() - 1 - path_planner->my_heuristic[path_planner->start_location];
    }
};

struct Neighbor
{
    vector<int> agents;
    int sum_of_costs;
    int old_sum_of_costs;
    set<pair<int, int>> colliding_pairs;  // id1 < id2
    set<pair<int, int>> old_colliding_pairs;  // id1 < id2
    vector<Path> old_paths;
};



struct BanditStats {
    vector<double> destroy_weights;
    vector<double> destroy_weights_squared;
    vector<double> destroy_counts;
    vector<std::deque<double>> recent_rewards; // Only used for AlphaUCB and EpsilonGreedy
    int banditIndex;
};

class BasicLNS
{
public:
    // statistics
    int num_of_failures = 0; // #replanning that fails to find any solutions
    list<IterationStats> iteration_stats; //stats about each iteration
    double runtime = 0;
    double average_group_size = -1;
    int sum_of_costs = 0;

    BasicLNS(const Instance& instance, double time_limit, int neighbor_size, int screen, const string & bandit_algorithm_name, int neighborhoodSizes,int numberOfDestroyHeuristics, double alphaUCB, double initialEpsilon, double lambdaDecay,double decayWindow);
    
    
    virtual ~BasicLNS()
    {
        for(auto it = neighborhoodBanditStats.begin(); it != neighborhoodBanditStats.end(); ++it)
        {
            delete *it;
        }
        neighborhoodBanditStats.clear();
        for(auto& stats : heuristicBanditStats.recent_rewards)
    {
        stats.clear();
    }
    heuristicBanditStats.recent_rewards.clear(); // Clear the deque
    heuristicBanditStats.recent_rewards.shrink_to_fit();
    }
    virtual string getSolverName() const = 0;
protected:
    // input params
    const Instance& instance; // avoid making copies of this variable as much as possible
    double time_limit;
    double replan_time_limit; // time limit for replanning
    int neighbor_size;
    int neighbor_arm_index;
    int screen;
    bandit_type bandit_algorithm = RANDOM_BANDIT;
    const string& bandit_algorithm_name;

    // Bandit hyperparameter
    int ucb1Constant = 1000;
    double mu0 = 0;
	double lambda0 = 0.01;
	double alpha0 = 1;
	double beta0 = 100;
    std::mt19937 generator;
    int iterationCount = 0;
    double alphaUCB = 10000;
    double initialEpsilon = 0.5;
    double lambdaDecay = 0.01;
    double decayWindow = 100;
    double epsilonT = initialEpsilon;

    // adaptive LNS
    bool ALNS = false;
    double decay_factor = -1;
    double reaction_factor = -1;
    int selected_neighbor;
    int numberOfNeighborhoodSizeCandidates;
    int numberOfDestroyHeuristics;
    
    // helper variables
    high_resolution_clock::time_point start_time;
    Neighbor neighbor;
    void initBandits(const int numberOfArms, const double decay);

    /**
     * Updates the bi-level approach with an observed reward.
     * according to Figure 1 in the paper (Line 12, Algorithm 1).
     */
    void sampleDestroyHeuristicAndNeighborhoodSize();

    /**
     * Invokes the bi-level approach to select a destroy heuristic and neighborhood size
     * according to Figure 1 in the paper (Line 5, Algorithm 1).
     */
    void updateDestroyAndNeighborhoodWeights(const double value, const bool condition);
    BanditStats heuristicBanditStats;
    vector<BanditStats*> neighborhoodBanditStats;

    /**
     * Concrete algorithms for multi-armed bandits like roulette wheel selection, UCB1, and Thompson Sampling
     * according to Section 4.2 in the paper.
     */
    int sampleDestroyHeuristic(BanditStats* stats);
    void updateDestroyWeights(BanditStats* stats, const double value, const bool condition);
};