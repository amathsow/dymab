#!/bin/bash

# Array of time limits
nb_agents=(200 500 800)


# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each time limit
    for k in "${nb_agents[@]}"
    do
        # Construct the scenario file name
        scenario_file="den520d.map-scen-random/den520d-random-${scenario_number}.scen" 
        #scenario_file="random_linkoping/linkoping_572-${scenario_number}.scen"

        
        # Base command with the dynamic scenario file
        #base_command="./balance -m den520d.map -a $scenario_file -o test -k 400 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --decayWindow=100 --lambdaDecay=5"
        base_command="./address -m den520d.map -a $scenario_file -o test -t 120 --stats "stats.txt" --outputPaths=paths.txt --seed=0 --screen=1 --maxIterations=1000000 --destroyStrategy=RandomWalk --algorithm=bernoulie --k=64"

        echo "Running command with -a $scenario_file and -k $k"
        $base_command -k $k
    done
done
