#!/bin/bash

# Array windows
windows=(10 20 50  80 100)



# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each window
    for w in "${windows[@]}"
    do
        # Construct the scenario file name
        scenario_file="Berlin_1_256.map-scen-random/Berlin_1_256-random-${scenario_number}.scen"
        
        # Base command with the dynamic scenario file
        base_command="./dymab -m Berlin_1_256.map -a $scenario_file -o test -k 1000 -t 120 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=50000 --lambdaDecay=5"

        echo "Running command with -a $scenario_file and  --decayWindow $w"
        $base_command --decayWindow $w
    done
done
