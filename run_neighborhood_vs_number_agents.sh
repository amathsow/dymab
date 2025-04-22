#!/bin/bash

# Array of time limits
nb_agents=(100 200 300)


# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each time limit
    for k in "${nb_agents[@]}"
    do
        # Construct the scenario file name
        scenario_file="random-64-64-10.map-scen-random/random-64-64-10-random-${scenario_number}.scen" 
        #scenario_file="random_linkoping/linkoping_572-${scenario_number}.scen"

        
        # Base command with the dynamic scenario file
        #base_command="./balance -m den520d.map -a $scenario_file -o test -k 400 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --decayWindow=100 --lambdaDecay=5"
        base_command="./dymab -m random-64-64-10.map -a $scenario_file -o test -t 100 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=100000 --decayWindow=100 --lambdaDecay=5 --destroyStrategy=Adaptive"

        echo "Running command with -a $scenario_file and -k $k"
        $base_command -k $k
    done
done
