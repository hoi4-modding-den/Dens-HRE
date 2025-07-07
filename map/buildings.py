# Should be done in conjunction with unitstacks.py and unitparse.py

import csv
import math
import os
import re
# As with unitstacks.py, must install Pillow first.
from PIL import Image
from collections import defaultdict

csv_path = "definition.csv"
province_path = "provinces.bmp"
heightmap_path = "heightmap.bmp"
buildings_path = "buildings.txt"
states_path = "../history/states"

# Default Values
DEFAULT_ROTATION = 0.0

# Buildings that are specific for coastal - Update with new changes to base game
NAVAL_BUILDINGS = ['naval_base_spawn', 'dockyard', 'floating_harbor']

print("Starting Program...")

# Parse the state file listed to get the provinces
def parse_state_file(state_file_path):
    """Parse a state file to extract state ID and province list"""
    state_id = None
    provinces = []

    # Try to read the state file
    try:
        with open(state_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Find state ID
            id_match = re.search(r'id\s*=\s*(\d+)', content)
            if id_match:
                state_id = int(id_match.group(1))
            
            # Find provinces block
            provinces_match = re.search(r'provinces\s*=\s*\{([^}]+)\}', content, re.DOTALL)
            if provinces_match:
                provinces_text = provinces_match.group(1)
                # Extract all numbers from the provinces block
                province_numbers = re.findall(r'\d+', provinces_text)
                provinces = [int(p) for p in province_numbers]
    
    except Exception as e:
        print(f"Error parsing {state_file_path}: {e}")
    
    return state_id, provinces

# Find a given state based on its ID
def find_state_by_id(target_state_id, states_directory):
    """Find state file by ID and return province list"""
    # If the directory for states does not exist, return an error
    if not os.path.exists(states_directory):
        print(f"Error: States directory not found: {states_directory}")
        return None
    
    # Otherwise, search through the state directory
    for filename in os.listdir(states_directory):
        # Check each .txt file
        if filename.endswith('.txt'):
            file_path = os.path.join(states_directory, filename)
            # See if the current state selected matches the id the user provided
            state_id, provinces = parse_state_file(file_path)
            
            # If a match, return the provinces for that state
            if state_id == target_state_id:
                print(f"Found state {state_id} in file: {filename}")
                print(f"Provinces in state: {len(provinces)}")
                return provinces
    
    print(f"Error: State {target_state_id} not found in any state files")
    return None

# Load province data from definition.csv - See unitstacks.py
def load_province_data(csv_path):
    """Load province data from definition.csv"""
    prov_id_to_rgb = {}
    prov_id_to_coastal = {}
    sea_provinces = {}
    
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            try:
                if not row or len(row) < 8:
                    continue
                
                prov_id = int(row[0])
                r, g, b = map(int, row[1:4])
                province_type = row[4].strip().lower()
                is_coastal = row[5].strip().lower() == 'true'
                
                if province_type == 'land':
                    prov_id_to_rgb[prov_id] = (r, g, b)
                    prov_id_to_coastal[prov_id] = is_coastal
                elif province_type == 'sea':
                    sea_provinces[prov_id] = (r, g, b)
                    
            except (ValueError, IndexError):
                continue
                
    return prov_id_to_rgb, prov_id_to_coastal, sea_provinces

# Calculate the center of each province - See unitstacks.py
def compute_province_centers(province_bmp, province_data):
    """Compute the center coordinates for all provinces"""
    image = Image.open(province_bmp).convert("RGB")
    width, height = image.size
    rgb_to_pixels = defaultdict(list)

    print(f"Processing {width}x{height} province map...")
    
    for y in range(height):
        z = height - 1 - y
        for x in range(width):
            color = image.getpixel((x, y))
            rgb_to_pixels[color].append((x, z))

    centers = {}
    for prov_id, rgb in province_data.items():
        pixels = rgb_to_pixels.get(rgb)
        if pixels:
            xs, zs = zip(*pixels)
            cx = sum(xs) / len(xs)
            cz = sum(zs) / len(zs)
            centers[prov_id] = (cx, cz)

    return centers

# Get the Y position for a given coordinate - See unitstacks.py
def get_height_at(x, z, heightmap_bmp):
    """Get height value from heightmap at given coordinates"""
    width, height = heightmap_bmp.size
    if 0 <= int(x) < width and 0 <= int(z) < height:
        gray = heightmap_bmp.getpixel((int(x), int(z)))
        if isinstance(gray, tuple):
            gray = gray[0]
        return (gray / 255) * 25.5
    return 0.0

# Finds the nearest sea province from the center of the province, used for coastal provinces to generate naval buildings
def find_nearest_sea_province(land_center, sea_centers):
    """Find the nearest sea province to a given land province"""
    # If there are no sea provinces, return a 0
    if not sea_centers:
        return 0
    
    # Set the initial minimum distance to infinity and nearest sea to 0
    min_distance = float('inf')
    nearest_sea = 0
    
    # Store the land center coordinates as a tuple
    land_x, land_z = land_center
    
    # For each sea province, calculate the distance to the land center
    for sea_id, (sea_x, sea_z) in sea_centers.items():
        distance = math.sqrt((land_x - sea_x)**2 + (land_z - sea_z)**2)
        # If the current sea province is closer than the current minimum, update it
        if distance < min_distance:
            min_distance = distance
            nearest_sea = sea_id

    return nearest_sea

# Load the existing buildings from buildings.txt for the given state
def load_existing_buildings(buildings_path, state_id):
    """Load existing buildings for the specified state"""
    existing_buildings = []
    
    try:
        # Open buildings.txt and parse it
        with open(buildings_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('//'):
                    try:
                        parts = line.split(';')
                        if len(parts) >= 7 and int(parts[0]) == state_id:
                            existing_buildings.append(line)
                    except (ValueError, IndexError):
                        continue
    except FileNotFoundError:
        print(f"Warning: {buildings_path} not found")
    
    return existing_buildings

# Generate building entries for the given state
def generate_building_entries(state_id, province_ids, land_centers, sea_centers, 
                            prov_id_to_coastal, heightmap_bmp, building_types):
    """Generate building entries for the specified provinces"""
    entries = []
    
    # For each province
    for prov_id in province_ids:
        # Ensure the province actually exists on the province map first
        if prov_id not in land_centers:
            print(f"Warning: Province {prov_id} not found in province map")
            continue
        
        # Store the information about the province in local variables
        is_coastal = prov_id_to_coastal.get(prov_id, False)
        x, z = land_centers[prov_id]
        y = get_height_at(x, z, heightmap_bmp)
        
        # Find nearest sea province if coastal
        adjacent_sea = 0
        if is_coastal:
            adjacent_sea = find_nearest_sea_province((x, z), sea_centers)
        
        # Generate entries ONLY for the building types the user selected
        for building_type in building_types:
            # For naval buildings, only generate if province is coastal
            if building_type in NAVAL_BUILDINGS and not is_coastal:
                continue
            
            # Use adjacent sea province for naval buildings, 0 for others
            sea_province = adjacent_sea if building_type in NAVAL_BUILDINGS else 0
            
            entry = f"{state_id};{building_type};{x:.2f};{y:.2f};{z:.2f};{DEFAULT_ROTATION:.2f};{sea_province}"
            entries.append(entry)
    
    return entries

# Write the generated buildings to a temp file
def write_buildings_output(existing_buildings, new_entries, output_path, include_existing=True):
    """Write buildings to output file"""
    # If the user wants to include existing buildings, combine them with new entries
    if include_existing:
        all_entries = existing_buildings + new_entries
        print(f"Writing {len(existing_buildings)} existing + {len(new_entries)} new entries")
    # Otherwise, only output generated buildings
    else:
        all_entries = new_entries
        print(f"Writing {len(new_entries)} new entries only")
    
    # Sort by state ID, then by building type
    def get_sort_key(line):
        if line.startswith('//') or ';' not in line:
            return (0, '')
        try:
            parts = line.split(';')
            state_id = int(parts[0])
            building_type = parts[1]
            return (state_id, building_type)
        except (ValueError, IndexError):
            return (999999, 'zzz')
    
    all_entries.sort(key=get_sort_key)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in all_entries:
            f.write(entry + '\n')

def main():
    # User input for state ID
    state_id = int(input("Enter the State ID: "))
    
    # Find and parse the state file
    print(f"\nSearching for state {state_id} in {states_path}...")
    province_ids = find_state_by_id(state_id, states_path)
    
    # If the state has no provinces, exit
    if province_ids is None:
        print("Exiting...")
        return
    
    # Otherwise, output the number of provinces in the state for user verification
    print(f"Found {len(province_ids)} provinces in state {state_id}")
    print(f"Province IDs: {province_ids[:10]}{'...' if len(province_ids) > 10 else ''}")
    
    # Output the available building types
    print("\nAvailable building types:")
    print("- arms_factory")
    print("- industrial_complex")
    print("- air_base")
    print("- naval_base")
    print("- naval_base_spawn")
    print("- dockyard")
    print("- bunker")
    print("- coastal_bunker")
    print("- anti_air_building")
    print("- synthetic_refinery")
    print("- nuclear_reactor_spawn")
    print("- floating_harbor")
    
    # Comma separated list of building types to generate based on user input
    print("\nEnter building types to generate (comma-separated):")
    building_input = input("Building types: ").strip()
    
    # Parse and clean building types
    if not building_input:
        print("No building types specified. Exiting...")
        return
    
    building_types = [x.strip() for x in building_input.split(',') if x.strip()]
    
    if not building_types:
        print("No valid building types specified. Exiting...")
        return
    
    print(f"Selected building types: {building_types}")

    # Prompt user for whether to include existing buildings
    include_existing = input("Include existing buildings in output? (y/n): ").strip().lower() == 'y'
    
    # Set the output path for the buildings file - Feel free to modify
    output_path = f"buildings_state_{state_id}.txt"
    
    # Fetch the province data
    print("\nLoading province data...")
    prov_id_to_rgb, prov_id_to_coastal, sea_provinces = load_province_data(csv_path)
    print(f"Loaded {len(prov_id_to_rgb)} land provinces and {len(sea_provinces)} sea provinces")
    
    # Calculate the centers of provinces - both land and sea.
    print("Computing province centers...")
    land_centers = compute_province_centers(province_path, prov_id_to_rgb)
    sea_centers = compute_province_centers(province_path, sea_provinces)
    print(f"Computed centers for {len(land_centers)} land provinces and {len(sea_centers)} sea provinces")
    
    # Fetch the heightmap for calculating Y coordinates
    print("Loading heightmap...")
    heightmap = Image.open(heightmap_path).convert("L")
    
    # Fetch the existing buildings for the given state
    print("Loading existing buildings...")
    existing_buildings = load_existing_buildings(buildings_path, state_id)
    print(f"Found {len(existing_buildings)} existing buildings for state {state_id}")
    
    # Generate the buildings the user requested
    print("Generating building entries...")
    new_entries = generate_building_entries(
        state_id, province_ids, land_centers, sea_centers, 
        prov_id_to_coastal, heightmap, building_types
    )
    print(f"Generated {len(new_entries)} new building entries")
    
    # Show coastal province info
    coastal_provinces = [pid for pid in province_ids if prov_id_to_coastal.get(pid, False)]
    print(f"Coastal provinces in this state: {coastal_provinces}")
    
    # Write the output to the specified file
    print(f"Writing output to {output_path}...")
    write_buildings_output(existing_buildings, new_entries, output_path, include_existing)
    
    # Final output
    print(f"\nGenerated {len(new_entries)} building entries for state {state_id}")
    print(f"Output written to {output_path}")

if __name__ == "__main__":
    main()