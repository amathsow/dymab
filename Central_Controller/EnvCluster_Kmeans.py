import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial import ConvexHull, convex_hull_plot_2d
from collections import defaultdict
import matplotlib.pyplot as plt

class UAVClusterManager:
    def __init__(self, uavs, map_size, obstacles, min_samples=2, xi=0.1, min_cluster_size=3):
        """
        Initializes the UAVClusterManager with UAV data, map size, and obstacles.

        Args:
            uavs (list): List of UAV dictionaries with 'start', 'goal', and 'name'.
            map_size (tuple): Size of the map as (width, height).
            obstacles (list): List of obstacle coordinates.
            min_samples (int): Minimum number of samples to form a cluster.
            xi (float): Parameter for cluster formation.
            min_cluster_size (int): Minimum size of clusters.
        """
        self.uavs = uavs
        self.map_size = map_size
        self.obstacles = obstacles
        self.min_samples = min_samples
        self.xi = xi
        self.min_cluster_size = min_cluster_size
        self.sub_maps = {}
        self.labels = None
        self.data = None
        self._create_clusters_and_sub_maps()

    def _create_clusters_and_sub_maps(self):
        """
        Creates clusters for UAVs and defines sub-maps for each cluster.
        """
        positions = []
        uav_identifiers = []

        for uav in self.uavs:
            positions.extend([uav['start'], uav['goal']])
            uav_identifiers.extend([uav['name']] * 2)

        positions = np.array(positions)

        if positions.size > 0:
            kmeans = KMeans(n_clusters=2, random_state=0)
            self.labels = kmeans.fit_predict(positions)
            
            clusters = defaultdict(list)
            for idx, label in enumerate(self.labels):
                uav_name = uav_identifiers[idx]
                if uav_name not in clusters[label]:
                    clusters[label].append(uav_name)

            for label, uav_names in clusters.items():
                cluster_uavs = [uav for uav in self.uavs if uav['name'] in uav_names]
                all_positions = [pos for uav in cluster_uavs for pos in (uav['start'], uav['goal'])]
                
                if len(all_positions) < 3:
                    continue  # Convex hull requires at least 3 points
                
                all_positions = np.array(all_positions)
                hull = ConvexHull(all_positions)
                
                hull_points = all_positions[hull.vertices]
                min_x, min_y = np.min(hull_points, axis=0)
                max_x, max_y = np.max(hull_points, axis=0)

                # Ensure bounding box fits within the map
                min_x, max_x = max(0, min_x - 1), min(max_x + 1, self.map_size[0] - 1)
                min_y, max_y = max(0, min_y - 1), min(max_y + 1, self.map_size[1] - 1)

                self.sub_maps[label] = {
                    'bounding_box': {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y},
                    'uavs': cluster_uavs,
                    'hull': hull_points
                }

            self.sub_maps = self.resolve_overlaps_by_adjusting_hulls(self.sub_maps)
        else:
            print("Insufficient data for clustering.")

    def resolve_overlaps_by_adjusting_hulls(self, sub_maps):
        """
        Resolves overlaps among clusters by adjusting hulls.

        Args:
            sub_maps (dict): Dictionary of sub-maps with hulls and UAVs.

        Returns:
            dict: Updated sub-maps with adjusted hulls.
        """
        keys = list(sub_maps.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                key1, key2 = keys[i], keys[j]
                if self.hulls_overlap(sub_maps[key1]['hull'], sub_maps[key2]['hull']):
                    # Determine overlapping UAVs
                    uavs_key1 = {uav['name'] for uav in sub_maps[key1]['uavs']}
                    uavs_key2 = {uav['name'] for uav in sub_maps[key2]['uavs']}
                    overlapping_uavs = uavs_key1.intersection(uavs_key2)

                    # Remove overlapping UAVs 
                    sub_maps[key1]['uavs'] = [uav for uav in sub_maps[key1]['uavs'] if uav['name'] not in overlapping_uavs]

                    # Recalculate hull 
                    if sub_maps[key1]['uavs']:
                        all_positions_key1 = [pos for uav in sub_maps[key1]['uavs'] for pos in (uav['start'], uav['goal'])]
                        if len(all_positions_key1) < 3:
                            continue
                        all_positions_key1 = np.array(all_positions_key1)
                        hull = ConvexHull(all_positions_key1)
                        hull_points = all_positions_key1[hull.vertices]
                        min_x_key1, min_y_key1 = np.min(hull_points, axis=0)
                        max_x_key1, max_y_key1 = np.max(hull_points, axis=0)

                        min_x_key1, max_x_key1 = max(0, min_x_key1 - 1), min(max_x_key1 + 1, self.map_size[0] - 1)
                        min_y_key1, max_y_key1 = max(0, min_y_key1 - 1), min(max_y_key1 + 1, self.map_size[1] - 1)

                        sub_maps[key1]['bounding_box'] = {'min_x': min_x_key1, 'min_y': min_y_key1, 'max_x': max_x_key1, 'max_y': max_y_key1}
                        sub_maps[key1]['hull'] = hull_points
                    else:
                        del sub_maps[key1]

        return sub_maps

    def hulls_overlap(self, hull1, hull2):
        """
        Checks if two convex hulls overlap.

        Args:
            hull1 (np.array): Points of the first convex hull.
            hull2 (np.array): Points of the second convex hull.

        Returns:
            bool: True if the hulls overlap, False otherwise.
        """
        # Convert hulls to polygons and check for overlap
        from shapely.geometry import Polygon
        poly1 = Polygon(hull1)
        poly2 = Polygon(hull2)
        return poly1.intersects(poly2)

    def get_sub_maps(self):
        """
        Retrieves the sub-maps.

        Returns:
            dict: Dictionary of sub-maps with bounding boxes, UAVs, and hulls.
        """
        return self.sub_maps

    def create_map_file(self, cluster_id, cluster_data):
        """
        Creates a map file and scenario file for a given cluster.

        Args:
            cluster_id (int): Identifier for the cluster.
            cluster_data (dict): Data of the cluster including bounding box and UAVs.

        Returns:
            int: Number of UAVs in the cluster.
        """
        bounding_box = cluster_data['bounding_box']
        uavs = cluster_data['uavs']
        width = bounding_box['max_x'] - bounding_box['min_x'] + 1
        height = bounding_box['max_y'] - bounding_box['min_y'] + 1

        scen_filename = f"submap_{cluster_id}.scen"
        uav_count = len(uavs)
        grid = [['.' for _ in range(width)] for _ in range(height)]

        for x, y in self.obstacles:
            if bounding_box['min_x'] <= x <= bounding_box['max_x'] and bounding_box['min_y'] <= y <= bounding_box['max_y']:
                grid[y - bounding_box['min_y']][x - bounding_box['min_x']] = '@'

        map_filename = f"submap_{cluster_id}.map"
        with open(map_filename, 'w') as file:
            file.write("type octile\n")
            file.write(f"height {height}\n")
            file.write(f"width {width}\n")
            file.write("map\n")
            for row in grid:
                file.write(''.join(row) + '\n')

        with open(scen_filename, 'w') as file:
            file.write("version 1\n")
            for idx, uav in enumerate(uavs):
                start_x = uav['start'][0] - bounding_box['min_x']
                start_y = uav['start'][1] - bounding_box['min_y']
                goal_x = uav['goal'][0] - bounding_box['min_x']
                goal_y = uav['goal'][1] - bounding_box['min_y']
                optimal_length = uav.get('optimal_length', -1)
                uav_id = uav.get('id', idx)
                file.write(f"{uav_id}\t{map_filename}\t{width}\t{height}\t{start_x}\t{start_y}\t{goal_x}\t{goal_y}\t{optimal_length:.8f}\n")

        print(f"Map file {map_filename} created with size {width}x{height}")

        return uav_count

    def plot_hulls(self):
        """
        Plots the convex hulls for visualization.
        """
        plt.figure()
        for key, data in self.sub_maps.items():
            hull_points = data['hull']
            if hull_points.size > 0:
                plt.fill(hull_points[:, 0], hull_points[:, 1], alpha=0.3, label=f"Cluster {key}")
        plt.legend()
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Convex Hulls of Clusters')
        plt.show()
