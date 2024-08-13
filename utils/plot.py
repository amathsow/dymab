import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

def process_csv(input_csv, output_csv):
    # Read the CSV file
    df = pd.read_csv(input_csv)
    
    # Calculate the max for 'runtime' and the sum for the other specified columns
    max_runtime = df['runtime'].max()
    sum_columns = df[['solution cost', 'lower bound', 'sum of distance', 'area under curve', 'number of agents']].sum()
    
    # Create a DataFrame with the results
    result = pd.DataFrame([[max_runtime] + sum_columns.tolist()], 
                          columns=['runtime', 'solution cost', 'lower bound', 'sum of distance', 'area under curve', 'number of agents'])
    
    
    try:
        existing_data = pd.read_csv(output_csv)
        header = False  # Do not write the header if the file already has content
    except FileNotFoundError:
        header = True  # Write the header if the file does not exist
    
    # Append the result to the output CSV file
    result.to_csv(output_csv, mode='a', header=header, index=False)


def plot_delay_vs_ll_runs(csv_files, titles):
    if len(csv_files) != 8:
        raise ValueError("Exactly 8 CSV files are required.")
    if len(titles) != 2:
        raise ValueError("Exactly 3 titles are required.")

    # Read CSV files into dataframes
    dataframes = [pd.read_csv(file) for file in csv_files]
    
    # Define colors and labels
    colors = ['red', 'blue', 'green', 'orange']
    labels = ['DyMAB(AlphaUCB)', 'C-DyMAB(AlphaUCB)', 'DyMAB(EpilonGreedy)', 'C-DyMAB(EpsilonGreedy)']
    
    # Dictionary to store grouped data for each configuration
    grouped_data = {}
    
    # Plot setup
    fig, axs = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
    
    
    for plot_index in range(2):
        for i in range(4):
            df = dataframes[plot_index * 4 + i]
            color = colors[i]
            label = labels[i]

            # Calculate the sum of delay
            df['sum of delay'] = df['solution cost'] - df['lower bound']
            df['runtime'] = df['runtime'].astype(int)
            
            # Group by runtime and calculate statistics
            grouped = df.groupby('runtime')['sum of delay'].agg(['mean', 'std', 'count']).reset_index()
            
            # Calculate the 95% confidence interval
            grouped['95% CI'] = 1.96 * (grouped['std'] / np.sqrt(grouped['count']))
            
            # Store grouped data for empirical best choice calculation
            grouped_data[(plot_index, label)] = grouped
            
            # Plot mean with error bars
            axs[plot_index].plot(grouped['runtime'], grouped['mean'], label=label, color=color)
            axs[plot_index].errorbar(grouped['runtime'], grouped['mean'], yerr=grouped['95% CI'], fmt='o', 
                                     ecolor=color, capsize=5, capthick=1, color=color)
        
        # Set title for each subplot
        axs[plot_index].set_title(titles[plot_index])
        axs[plot_index].set_xlabel('Runtime (seconds)')
        axs[plot_index].grid(True)
    
    # Set y-axis label for the first subplot
    axs[0].set_ylabel('Sum of Delays')
    
    # Set x-axis ticks and limits for each subplot
    axs[0].set_xticks([2, 4, 8, 16, 32, 64, 128, 180])
    axs[0].set_xlim(2, 180)
    
    axs[1].set_xticks([4, 8, 16, 32, 64, 128, 180])
    axs[1].set_xlim(4, 180)
    
     # Calculate the empirical best choice (minimum mean sum of delay across all configurations and runtimes)
    all_means = []
    for plot_index in range(2):
        for label in labels:
            all_means.append(grouped_data[(plot_index, label)]['mean'])
    all_means = pd.concat(all_means)
    empirical_best_value = all_means.min()
    
    # Plot empirical best choice as a horizontal line
    for plot_index in range(2):
        axs[plot_index].axhline(y=empirical_best_value, color='m', linestyle='--', label='Empirically Best Policy')
    
    
    # Set shared legend
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=5)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to make room for legend
    plt.show()



def plot_sum_of_delay_vs_agents(list_random, list_ost003d, list_berlin, list_dense, list_lkpg):
    colors = ['red', 'blue', 'green', 'orange', 'black', 'indigo']
    labels = ['DyMAB(AlphaUCB)', 'C-DyMAB(AlphaUCB)', 'DyMAB(EpsilonGreedy)', 'C-DyMAB(EpsilonGreedy)', 'Thompson', 'UCB1']
    lists = [list_random, list_ost003d, list_berlin, list_dense, list_lkpg]
    titles = ['Random', 'OST003D', 'Berlin', 'Dense', 'NewCity']
    
    fig = plt.figure(figsize=(18, 10))
    gs = fig.add_gridspec(2, 3)

    x_ticks_limits = [
        ([100, 200, 300], (100, 300)),
        ([200, 400, 600], (200, 600)),
        ([100, 200, 500, 800, 1000], (100, 1000)),
        ([200, 400, 800], (200, 800)),
        ([100, 500, 1000, 1500], (100, 1500))  
    ]

    # Creating the subplots
    axes = []
    for i in range(2):
        ax = fig.add_subplot(gs[0, i])
        axes.append(ax)
    for i in range(3):
        ax = fig.add_subplot(gs[1, i])
        axes.append(ax)

    for i, (data_list, title, ax, (xticks, xlim)) in enumerate(zip(lists, titles, axes, x_ticks_limits)):
        all_data = []
        for file, label in zip(data_list, labels):
            try:
                # Load the data into a DataFrame
                df = pd.read_csv(file)
                
                # Calculate the sum of delay for each entry
                df['sum of delay'] = abs(df['solution cost'] - df['lower bound'])
                
                # Add label for the legend
                df['label'] = label
                
                # Append the processed data to the list
                all_data.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
                continue
        
        if not all_data:
            print(f"No valid data for {title}")
            continue
        
        # Concatenate all data into a single DataFrame
        concatenated_data = pd.concat(all_data)
        
        # Group by 'number of agents', 'label' and calculate mean, std, count, and 95% CI
        grouped = concatenated_data.groupby(['number of agents', 'label'])['sum of delay'].agg(['mean', 'std', 'count']).reset_index()
        grouped['95% CI'] = 1.96 * (grouped['std'] / np.sqrt(grouped['count']))

        # Plotting
        for label, color in zip(labels, colors):
            data = grouped[grouped['label'] == label]
            ax.plot(data['number of agents'], data['mean'], label=label, color=color, marker='o')
            ax.fill_between(data['number of agents'], data['mean'] - data['95% CI'], data['mean'] + data['95% CI'], color=color, alpha=0.2)
        
        # Set x-axis limits and ticks
        ax.set_xticks(xticks)
        ax.set_xlim(xlim)
        ax.set_title(title)
        ax.grid(True)
    
    # Hide the empty subplot to center the second row
    #fig.delaxes(axes[2])
    
    # Adjust the layout to center the second row
    gs.update(wspace=0.5, hspace=0.5)
    
    
    # Set common labels
    fig.text(0.5, 0.04, 'Number of agents', ha='center', fontsize=12)
    fig.text(0.04, 0.5, 'Sum of Delays', va='center', rotation='vertical', fontsize=12)
   
    # Add a single legend for all subplots
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()



## plot sum of delays vs number agents
def plot_sum_of_delay_vs_agents1(list_random, list_ost003d, list_berlin, list_dense):
    colors = ['red', 'blue', 'green', 'orange', 'black', 'indigo']
    labels = ['DyMAB(AlphaUCB)', 'C-DyMAB(AlphaUCB)', 'DyMAB(EpsilonGreedy)', 'C-DyMAB(EpsilonGreedy)', 'Thompson', 'UCB1']
    lists = [list_random, list_ost003d, list_berlin, list_dense]
    titles = ['Random', 'OST003D', 'Berlin', 'Dense']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    x_ticks_limits = [
        ([100, 200, 300], (100, 300)),
        ([200, 400, 600], (200, 600)),
        ([100, 200, 500, 800, 1000], (100, 1000)),
        ([200, 400, 800], (200, 800))
    ]

    for i, (data_list, title, ax, (xticks, xlim)) in enumerate(zip(lists, titles, axes, x_ticks_limits)):
        all_data = []
        for file, label in zip(data_list, labels):
            # Load the data into a DataFrame
            df = pd.read_csv(file)
            
            # Calculate the sum of delay for each entry
            df['sum of delay'] = abs(df['solution cost'] - df['lower bound'])
            
            # Add label for the legend
            df['label'] = label
            
            # Append the processed data to the list
            all_data.append(df)
        
        # Concatenate all data into a single DataFrame
        concatenated_data = pd.concat(all_data)
        
        # Group by 'number of agents', 'label' and calculate mean, std, count, and 95% CI
        grouped = concatenated_data.groupby(['number of agents', 'label'])['sum of delay'].agg(['mean', 'std', 'count']).reset_index()
        grouped['95% CI'] = 1.96 * (grouped['std'] / np.sqrt(grouped['count']))

        # Plotting
        for label, color in zip(labels, colors):
            data = grouped[grouped['label'] == label]
            ax.plot(data['number of agents'], data['mean'], label=label, color=color, marker='o')
            ax.fill_between(data['number of agents'], data['mean'] - data['95% CI'], data['mean'] + data['95% CI'], color=color, alpha=0.2)
        
        # Set x-axis limits and ticks
        ax.set_xticks(xticks)
        ax.set_xlim(xlim)
        ax.set_title(title)
        ax.grid(True)

    # Set common labels
    axes[0].set_ylabel('Sum of Delays')
    axes[2].set_ylabel('Sum of Delays')
    axes[2].set_xlabel('Number of agents')
    axes[3].set_xlabel('Number of agents')
   
   

    # Add a single legend for all subplots
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

## experiment 2 : sum of deays vs decay window
def plot_delays_vs_decaywindow1(csv_list):
    # Check if the list is not empty
    if not csv_list:
        raise ValueError("The list of CSV files should not be empty")

    plt.figure(figsize=(12, 7))

    # Define alpha values for labeling
    alpha_values = [100, 1000, 5000, 10000]

    # Loop through each CSV file and corresponding alpha value
    for csv_file, alpha in zip(csv_list, alpha_values):
        # Read the CSV file
        df = pd.read_csv(csv_file)

        # Ensure the necessary columns are present
        if not all(col in df.columns for col in ['decayWindow', 'solution cost', 'lower bound']):
            raise ValueError("CSV files must contain 'decayWindow', 'solution cost', and 'lower bound' columns")

        # Calculate delays
        df['delay'] = df['solution cost'] - df['lower bound']

        # Group by decayWindow and calculate mean and confidence intervals
        grouped = df.groupby('decayWindow')['delay'].agg(['mean', 'count', 'std'])
        grouped['sem'] = grouped['std'] / np.sqrt(grouped['count'])  # Standard error of the mean
        grouped['ci95_hi'] = grouped['mean'] + 1.96 * grouped['sem']  # 95% confidence interval high
        grouped['ci95_lo'] = grouped['mean'] - 1.96 * grouped['sem']  # 95% confidence interval low
        grouped['error'] = 1.96 * grouped['sem']  # Error for errorbar

        # Plotting
        plt.errorbar(grouped.index, grouped['mean'], yerr=grouped['error'], marker='o', linestyle='-', label=f'Alpha={alpha}')

    plt.xticks([10, 20, 50, 80, 100])
    plt.xlim(10, 100)

    plt.title('DyMAB(AlphaUCB): Berlin 800 agents')
    plt.xlabel('Decay Window')
    plt.ylabel('Sum of Delays')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_delays_vs_decaywindow(list_alpha_berlin400, list_alpha_berlin800, list_epsilon_berlin400, list_epsilon_berlin800):
    # Define alpha and epsilon values for labeling
    alpha_values = [10, 100, 1000, 5000, 10000]
    epsilon_values = [0.1, 0.25, 0.5, 0.75, 1]

    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12), sharey=False)
    #fig.suptitle('Berlin Map', fontsize=16 * 4)  # Title font size scaled up by 4

    strategies = [
        (list_alpha_berlin400, 'DyMAB(α-UCB) 400 agents', alpha_values, axes[0, 0], 'α'),
        (list_alpha_berlin800, 'DyMAB(α-UCB) 800 agents', alpha_values, axes[1, 0], 'α'),
        (list_epsilon_berlin400, 'DyMAB(ε-Greedy) 400 agents', epsilon_values, axes[0, 1], 'ε'),
        (list_epsilon_berlin800, 'DyMAB(ε-Greedy) 800 agents', epsilon_values, axes[1, 1], 'ε')
    ]

    for csv_list, title, values, ax, param_symbol in strategies:
        summary_df = pd.DataFrame()

        # Loop through each CSV file and corresponding alpha/epsilon value
        for csv_file, value in zip(csv_list, values):
            # Read the CSV file
            df = pd.read_csv(csv_file)

            # Ensure the necessary columns are present
            if not all(col in df.columns for col in ['decayWindow', 'solution cost', 'lower bound']):
                raise ValueError("CSV files must contain 'decayWindow', 'solution cost', and 'lower bound' columns")

            # Calculate delays
            df['delay'] = df['solution cost'] - df['lower bound']

            # Group by decayWindow and calculate mean delay
            grouped = df.groupby('decayWindow')['delay'].mean().reset_index()
            grouped['value'] = value

            # Append to summary DataFrame
            summary_df = pd.concat([summary_df, grouped])

        # Pivot the DataFrame for plotting
        pivot_df = summary_df.pivot(index='decayWindow', columns='value', values='delay')
        pivot_df.plot(kind='bar', ax=ax)

        ax.tick_params(axis='y', labelsize=8 * 2)

        ax.set_title(title, fontsize=12 * 2)  # Title font size scaled up by 4
        ax.set_xlabel('Decay Window' if '800 agents' in title else '', fontsize=10 * 2)  # Label font size scaled up by 4
        ax.set_ylabel('Sum of Delays', fontsize=10 * 2)  # Label font size scaled up by 4
        ax.legend(title=f'{param_symbol}', fontsize=8 * 2, title_fontsize=10 * 2)  # Legend font size scaled up by 4
        ax.grid(True)
        ax.set_xticks(range(len(pivot_df.index)))
        ax.set_xticklabels(pivot_df.index, rotation=0, fontsize=8 * 2)  # Tick label font size scaled up by 4

        # Set y-axis limit and remove x-axis label for 400 agents plots
        if '400 agents' in title:
            ax.set_ylim(0, 200)
            ax.set_xlabel('')
            
        if '800 agents' in title:
            ax.set_xlabel('Decay Window', fontsize=10 * 2)  # Label font size scaled up by 4

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()
