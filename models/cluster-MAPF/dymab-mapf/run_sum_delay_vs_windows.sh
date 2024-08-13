#!/bin/bash

# Array of time limits
windows=(10 20 50  80 100)
#windows=(10)


# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each window
    for w in "${windows[@]}"
    do
        # Construct the scenario file name
        #scenario_file="Berlin_1_256.map-scen-random/Berlin_1_256-random-${scenario_number}.scen"
        scenario_file="random_linkoping/linkoping_572-${scenario_number}.scen"
        
        # Base command with the dynamic scenario file
        #base_command="./balance -m den520d.map -a $scenario_file -o test -k 400 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --decayWindow=100 --lambdaDecay=5"
        base_command="./balance -m Linkoping_1000x572.map -a $scenario_file -o test -k 1000 -t 120 --outputPaths=paths.txt --banditAlgo=EpsilonGreedy --neighborCandidateSizes=5 --seed=0 --alphaUCB=10000 --lambdaDecay=5 --initialEpsilon=1"

        echo "Running command with -a $scenario_file and  --decayWindow $w"
        $base_command --decayWindow $w
    done
done
