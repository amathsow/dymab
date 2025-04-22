#!/bin/bash

# Array of time limits
neighborhood=(4 8 12 16)



# Loop through scenario numbers
for scenario_number in {1..25}
do
    # Loop through each window
    for n in "${neighborhood[@]}"
    do
        # Construct the scenario file name
        scenario_file="random-64-64-10.map-scen-random/random-64-64-10-random-${scenario_number}.scen"
        
        # Base command with the dynamic scenario file
        base_command="./dymab -m random-64-64-10.map -a $scenario_file -o test -k 200 -t 100 --outputPaths=paths.txt --banditAlgo=AlphaUCB --neighborCandidateSizes=5 --seed=0 --alphaUCB=50000 --decayWindow=100 --lambdaDecay=10 --destroyStrategy=Hotspots"

        echo "Running command with -a $scenario_file and  --neighborSize $n"
        $base_command --neighborSize $n
    done
done
