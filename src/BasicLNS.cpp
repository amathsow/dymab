#include "BasicLNS.h"
#include <numeric>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <cassert>
#include <random>

// Constructor for BasicLNS
BasicLNS::BasicLNS(const Instance& instance, double time_limit, int neighbor_size, int screen, const std::string & bandit_algorithm_name, int neighborhoodSizes, int numberOfDestroyHeuristics, double alphaUCB, double initialEpsilon, double lambdaDecay, double decayWindow)
    : instance(instance), time_limit(time_limit), neighbor_size(neighbor_size), screen(screen), bandit_algorithm_name(bandit_algorithm_name),
      ucb1Constant(100), numberOfNeighborhoodSizeCandidates(neighborhoodSizes), numberOfDestroyHeuristics(numberOfDestroyHeuristics),
      alphaUCB(alphaUCB), initialEpsilon(initialEpsilon), lambdaDecay(lambdaDecay), decayWindow(decayWindow), iterationCount(0), epsilonT(initialEpsilon)
{


    heuristicBanditStats.recent_rewards.resize(numberOfDestroyHeuristics);
    heuristicBanditStats.banditIndex = 0;
    

    // Initialize neighborhoodBanditStats
    for (int i = 0; i < numberOfNeighborhoodSizeCandidates; ++i) {
        BanditStats* stats = new BanditStats();
        stats->recent_rewards.resize(numberOfDestroyHeuristics);
        neighborhoodBanditStats.push_back(stats);
    }
    
  

    // Initialize bandit algorithm type
    if (bandit_algorithm_name == "Random")
        bandit_algorithm = RANDOM_BANDIT;
    else if (bandit_algorithm_name == "Roulette")
        bandit_algorithm = ROULETTE_WHEEL;
    else if (bandit_algorithm_name == "UCB1")
        bandit_algorithm = UCB1;
    else if (bandit_algorithm_name == "Thompson")
        bandit_algorithm = THOMPSON_SAMPLING;
    else if (bandit_algorithm_name == "EpsilonGreedy")
        bandit_algorithm = EpsilonGreedy;
    else if (bandit_algorithm_name == "AlphaUCB")
        bandit_algorithm = AlphaUCB;
}

// Update destroy and neighborhood weights
void BasicLNS::updateDestroyAndNeighborhoodWeights(const double value, const bool condition)
{
    updateDestroyWeights(&heuristicBanditStats, value, condition);
    if (numberOfNeighborhoodSizeCandidates > 0) {
        updateDestroyWeights(neighborhoodBanditStats[selected_neighbor], value, condition);
    }
}

// Update destroy weights based on observed reward
void BasicLNS::updateDestroyWeights(BanditStats* stats, double new_reward, const bool condition)
{
    if (bandit_algorithm == RANDOM_BANDIT) return; // No update required for random bandit algorithm

    if (condition) {
        if (bandit_algorithm == AlphaUCB || bandit_algorithm == EpsilonGreedy) {
            
            auto& recent_rewards = stats->recent_rewards[stats->banditIndex];
            recent_rewards.push_back(new_reward);
            if (recent_rewards.size() > decayWindow) {
                recent_rewards.pop_front();
            }
            
            
        } else {
            stats->destroy_weights[stats->banditIndex] += new_reward;
            stats->destroy_weights_squared[stats->banditIndex] += new_reward * new_reward;
        }
    }
}

// Select destroy heuristic and neighborhood size
void BasicLNS::sampleDestroyHeuristicAndNeighborhoodSize()
{
    const int numberOfArms = heuristicBanditStats.destroy_weights.size();
    selected_neighbor = sampleDestroyHeuristic(&heuristicBanditStats);
    if (numberOfNeighborhoodSizeCandidates > 0) {
        neighbor_arm_index = sampleDestroyHeuristic(neighborhoodBanditStats[selected_neighbor]);
        neighbor_size = 1 << (neighbor_arm_index + numberOfNeighborhoodSizeCandidates);
       
    }
}


// Sample destroy heuristic using various bandit algorithms
int BasicLNS::sampleDestroyHeuristic(BanditStats* stats)
{
    const int numberOfArms = stats->destroy_weights.size();
    double weightSum = 0;
    double totalCount = std::accumulate(stats->destroy_counts.begin(), stats->destroy_counts.end(), 0.0);
    double r = (double)rand() / RAND_MAX;
    double threshold = stats->destroy_weights[0];
    //double currentEpsilon = initialEpsilon * exp(-lambdaDecay * iterationCount);
    // Update dynamic alpha
    double dynamicAlpha = alphaUCB / (1 + lambdaDecay * log(1 + iterationCount));

    for (int index = 0; index < numberOfArms; index++) {
        weightSum += stats->destroy_weights[index];
        totalCount += stats->destroy_counts[index];
    }

    if (bandit_algorithm == RANDOM_BANDIT) {
        stats->banditIndex = rand() % stats->destroy_weights.size();
    } else if (bandit_algorithm == ROULETTE_WHEEL) {
        double sum = weightSum;
        if (screen >= 2) {
            std::cout << "destroy weights = ";
            for (const auto& h : stats->destroy_weights)
                std::cout << h / sum << ",";
        }
        stats->banditIndex = 0;
        while (threshold < r * sum) {
            stats->banditIndex++;
            threshold += stats->destroy_weights[stats->banditIndex];
        }
    } else if (bandit_algorithm == UCB1) {
        double maxUCB1value = -std::numeric_limits<double>::max();
        for (int index = 0; index < numberOfArms; index++) {
            double numberOfRewards = stats->destroy_counts[index];
            double meanReward = stats->destroy_weights[index] / numberOfRewards;
            double currentUCB1value = 0;
            if (abs(numberOfRewards) < 1e-5) {
                currentUCB1value = std::numeric_limits<double>::infinity();
            } else {
                const double explorationTerm = sqrt(2 * log(totalCount) / numberOfArms);
                currentUCB1value = meanReward + ucb1Constant * explorationTerm;
            }
            if (currentUCB1value > maxUCB1value) {
                maxUCB1value = currentUCB1value;
                stats->banditIndex = index;
            }
        }
    } 
    
   else if (bandit_algorithm == AlphaUCB) {
    double maxAlphaUCBValue = -std::numeric_limits<double>::max();

        for (int index = 0; index < stats->destroy_weights.size(); ++index) {
            auto& recent_rewards = stats->recent_rewards[index];
            double sum_rewards = std::accumulate(recent_rewards.begin(), recent_rewards.end(), 0.0);
            int count = recent_rewards.size();
            double meanReward = count > 0 ? sum_rewards / count : 0;
            
            double explorationTerm = sqrt((2 * dynamicAlpha) / (count > 0 ? count : 1));
            double alphaUCBValue = meanReward + explorationTerm;

            if (alphaUCBValue > maxAlphaUCBValue) {
                maxAlphaUCBValue = alphaUCBValue;
                stats->banditIndex = index;
               // iterationCount++;
            }
            
        }
        iterationCount++;
}
    
    
    else if (bandit_algorithm == EpsilonGreedy) {
        std::uniform_real_distribution<> dis(0.0, 1.0);
        if (dis(generator) < epsilonT) {
            // Random heuristic
            stats->banditIndex = rand() % stats->destroy_weights.size();
        } else {
            // Best heuristic
            double maxAverageReward = -std::numeric_limits<double>::max();
            for (int index = 0; index < stats->destroy_weights.size(); ++index) {
                auto& recent_rewards = stats->recent_rewards[index];
                double sum_rewards = std::accumulate(recent_rewards.begin(), recent_rewards.end(), 0.0);
                int count = recent_rewards.size();
                double averageReward = count > 0 ? sum_rewards / count : 0;
                if (averageReward > maxAverageReward) {
                    maxAverageReward = averageReward;
                    stats->banditIndex = index;
                    //iterationCount++;
                }
            }
        }
        iterationCount++;
        // Use logarithmic decay for epsilonT
        epsilonT = initialEpsilon / log(1 + lambdaDecay * iterationCount);
        if (iterationCount % 100 == 0) {
            epsilonT = std::max(initialEpsilon, epsilonT * log(iterationCount));
        }
        
    } else if (bandit_algorithm == THOMPSON_SAMPLING) {
        double maxValue = -std::numeric_limits<double>::max();
        for (int index = 0; index < numberOfArms; index++) {
            double currentValue = 0;
            double n = stats->destroy_counts[index];
            double mean = stats->destroy_weights[index] / n;
            double mean_squared = stats->destroy_weights_squared[index] / n;
            double var = mean_squared - mean * mean;
            if (var < 0) {
                var = 0;
            }
            if (abs(n) < 1e-5) {
                currentValue = std::numeric_limits<double>::infinity();
            } else {
                const double delta = mean - mu0;
                const double lambda1 = lambda0 + n;
                assert(lambda1 > 0);
                const double mu1 = (lambda0 * mu0 + n * mean) / lambda1;
                const double alpha1 = alpha0 + n / 2;
                assert(alpha1 >= 1);
                const double beta1 = beta0 + 0.5 * (n * var + (lambda0 * n * delta * delta) / lambda1);
                assert(beta1 >= 0);
                std::gamma_distribution<> gd(alpha1, 1 / beta1);
                double gammaVariate = gd(generator);
                const double normalizedVariance = 1.0 / (lambda1 * gammaVariate);
                const double normalizedMean = mu1;
                std::normal_distribution<> nd{normalizedMean, sqrt(normalizedVariance)};
                currentValue = nd(generator);
            }
            if (currentValue > maxValue) {
                maxValue = currentValue;
                stats->banditIndex = index;
            }
        }
    }

   //terationCount++; // Increment the iteration count after selection

    return stats->banditIndex;
}

