#!/bin/bash

# Array of time limits
nb_agents=(3500 6000 8000 10000)


# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each time limit
    for k in "${nb_agents[@]}"
    do
        # Construct the scenario file name
        #scenario_file="Berlin_1_256.map-scen-random/Berlin_1_256-random-${scenario_number}.scen" 
        scenario_file="scen-warehouse/warehouse-20-40-10-2-2-10000agents-${scenario_number}.scen"

        
        # Base command with the dynamic scenario file
        #base_command="./balance -m den520d.map -a $scenario_file -o test -k 400 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --decayWindow=100 --lambdaDecay=5"
        base_command="./lns -m warehouse-20-40-10-2-2.map -a $scenario_file -o test -t 300 --outputPaths=paths.txt --seed=0 neighborSize=5"

        echo "Running command with -a $scenario_file and -k $k"
        $base_command -k $k
    done
done
