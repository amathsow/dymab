#!/bin/bash

# Array of time limits
time_limits=(16 64 256 400)


# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each time limit
    for t in "${time_limits[@]}"
    do
        # Construct the scenario file name
        scenario_file="random_linkoping/linkoping_572-${scenario_number}.scen"
        #scenario_file="den520d.map-scen-random/den520d-random-${scenario_number}.scen"
        
        # Base command with the dynamic scenario file
        #base_command="./balance -m den520d.map -a $scenario_file -o test -k 400 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --decayWindow=100 --lambdaDecay=5"
        base_command="./balance -m Linkoping_1000x572.map -a $scenario_file -o test -k 800 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --decayWindow=100 --lambdaDecay=5"

        echo "Running command with -a $scenario_file and -t $t"
        $base_command -t $t
    done
done
