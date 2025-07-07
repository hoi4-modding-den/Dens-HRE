import csv
# Before running, make sure to run pip `install pillow`
from PIL import Image
from collections import defaultdict

# All relevant files must be in the same directory. 
# This will parse the file names, but feel free to change the output path.

csv_path = "definition.csv"
province_path = "provinces.bmp"
heightmap_path = "heightmap.bmp"
unitstack_path = "unitstacks.txt"
output_path = "output_new.txt"

# Default values - Feel free to modify

DEFAULT_ROTATION = -1.57
DEFAULT_OFFSET = 0.2

print("Starting Program...")

# Load in definition.csv entries
def load_province_data(csv_path):
    # Creates arrays
    prov_id_to_rgb = {}
    prov_id_to_type = {}
    prov_id_to_coastal = {}
    # Open definition.csv
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            try:
                # Checks to make sure the current row is a valid definition
                if not row or len(row) < 8:
                    continue
                
                # Only process land provinces
                province_type = row[4].strip().lower()
                if province_type != 'land':
                    continue
                
                # Parse province data
                prov_id = int(row[0])
                r, g, b = map(int, row[1:4])
                is_coastal = row[5].strip().lower() == 'true'
                continent = int(row[7])
                
                # Add the values parsed from the entry to the arrays above
                prov_id_to_rgb[prov_id] = (r, g, b)
                prov_id_to_type[prov_id] = continent
                prov_id_to_coastal[prov_id] = is_coastal
            except (ValueError, IndexError):
                # Skip rows that can't be parsed
                continue
    return prov_id_to_rgb, prov_id_to_type, prov_id_to_coastal

# Fetch the existing unitstacks entries
def load_existing_unitstacks(txt_path):
    # Create a new set for existing entries
    existing = set()
    try:
        # Try to open the unitstacks file
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('//'):  # Skip comments
                    try:
                        # Split by semicolon and get first part (province ID)
                        parts = line.split(';')
                        if len(parts) >= 2:
                            prov_id = int(parts[0])
                            existing.add(prov_id)
                    except (ValueError, IndexError):
                        continue
    except FileNotFoundError:
        print(f"Warning: {txt_path} not found, assuming no existing entries")
    return existing

# Calculate the center of a given province for setting the position
def compute_prov_centers(province_bmp, prov_id_to_rgb):
    # Open province.bmp and get the dimensions
    image = Image.open(province_bmp).convert("RGB")
    width, height = image.size
    rgb_to_pixels = defaultdict(list)

    print(f"Processing {width}x{height} province map...")
    
    # Calculate the coordinates using the HOI4 coordinate system, and store the position
    for y in range(height):
        z = height - 1 - y
        for x in range(width):
            color = image.getpixel((x, y))
            rgb_to_pixels[color].append((x, z))

    # An array containing the center of each province
    centers = {}
    # For every province that was calculated
    for prov_id, rgb in prov_id_to_rgb.items():
        # Pull the province location based on the rgb value
        pixels = rgb_to_pixels.get(rgb)
        if pixels:
            # Calculations for finding the center
            xs, zs = zip(*pixels)
            cx = sum(xs) / len(xs)
            cz = sum(zs) / len(zs)
            centers[prov_id] = (cx, cz)

    return centers

# Calculate the Y position based on heightmap,bmp
def get_height_at(x, z, heightmap_bmp):
    # Get the dimensions of the heightmap
    width, height = heightmap_bmp.size
    # If within the bounds
    if 0 <= int(x) < width and 0 <= int(z) < height:
        # Get the current pixel
        gray = heightmap_bmp.getpixel((int(x), int(z)))
        # If it is a valid entry, store it in a temporary array
        if isinstance(gray, tuple):
            gray = gray[0]
        # Return the value after modifying to conform with HOI4 coordinate system bounds
        return (gray / 255) * 25.5
    return 0.0

# Generate missing entries for new provinces to unitstacks
def gen_missing_entries(prov_id_to_rgb, prov_id_to_coastal, existing_ids, centers, heightmap_bmp):
    new_entries = []

    # Unit types for coastal vs non-coastal provinces
    coastal_unit_types = list(range(39))  # All unit types 0-38 for coastal provinces
    non_coastal_unit_types = [0, 1, 2, 3, 4, 5, 6, 9, 10, 21, 22, 23, 24, 25, 26, 27, 38]  # Limited types for non-coastal

    # Get provinces that need unitstack entries
    missing_provinces = []
    for prov_id in sorted(prov_id_to_rgb.keys()):
        if prov_id not in existing_ids and prov_id in centers:
            missing_provinces.append(prov_id)

    # Generate entries sorted by unit type first, then province ID
    all_unit_types = set()
    
    # Collect all unit types that will be used
    for prov_id in missing_provinces:
        is_coastal = prov_id_to_coastal.get(prov_id, False)
        unit_types = coastal_unit_types if is_coastal else non_coastal_unit_types
        all_unit_types.update(unit_types)
    
    # Sort by unit type first, then by province ID
    for unit_type in sorted(all_unit_types):
        for prov_id in missing_provinces:
            is_coastal = prov_id_to_coastal.get(prov_id, False)
            unit_types = coastal_unit_types if is_coastal else non_coastal_unit_types
            
            if unit_type in unit_types:
                x, z = centers[prov_id]
                y = get_height_at(x, z, heightmap_bmp)
                
                new_entries.append("{0};{1};{2:.2f};{3:.2f};{4:.2f};{5:.2f};{6:.2f}".format(
                    prov_id, unit_type, x, y, z, DEFAULT_ROTATION, DEFAULT_OFFSET))

    return new_entries

# Write the output to a temporary file
def write_output(current_txt, new_entries, output_path):
    existing_lines = []
    
    # Read existing entries
    try:
        with open(current_txt, 'r', encoding='utf-8') as f:
            existing_lines = [line.rstrip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: {current_txt} not found, creating new file")
    
    all_lines = existing_lines + new_entries

    # Sort by unit type first, then by province ID
    def get_sort_key(line):
        if line.startswith('//') or ';' not in line:
            return (-1, 0)  # Comments go first
        try:
            parts = line.split(";")
            prov_id = int(parts[0])
            unit_type = int(parts[1]) if len(parts) > 1 else 0
            return (unit_type, prov_id)  # Sort by unit type first, then province ID
        except (ValueError, IndexError):
            return (999999, 999999)  # Invalid lines go last

    all_lines.sort(key=get_sort_key)

    with open(output_path, 'w', encoding='utf-8') as f:
        for line in all_lines:
            f.write(line + "\n")

# Main execution
print("Loading province data...")
prov_id_to_rgb, prov_id_to_type, prov_id_to_coastal = load_province_data(csv_path)
print(f"Loaded {len(prov_id_to_rgb)} land provinces from CSV")

if len(prov_id_to_rgb) == 0:
    print("ERROR: No land provinces loaded from CSV. Check file format and encoding.")
    exit(1)

print("Fetching existing unitstacks data...")
existing_ids = load_existing_unitstacks(unitstack_path)
print(f"Found {len(existing_ids)} existing provinces with unitstack entries")

print("Computing province centers from bitmap...")
centers = compute_prov_centers(province_path, prov_id_to_rgb)
print(f"Computed centers for {len(centers)} provinces")

print("Loading heightmap...")
heightmap = Image.open(heightmap_path).convert("L")

print("Generating missing entries for provinces...")
new_entries = gen_missing_entries(prov_id_to_rgb, prov_id_to_coastal, existing_ids, centers, heightmap)
print(f"Generated {len(new_entries)} new entries")

print(f"Missing provinces count: {len(missing_provinces)} ({coastal_count} coastal)")
if missing_provinces:
    print(f"Example missing provinces (first 10): {missing_provinces[:10]}")
    print(f"Highest province ID in definition: {max(prov_id_to_rgb.keys())}")

print(f"Example existing provinces (first 10): {sorted(list(existing_ids))[:10]}")
if existing_ids:
    print(f"Highest existing province ID: {max(existing_ids)}")

print("Writing output to file...")
write_output(unitstack_path, new_entries, output_path)

print("Generated {} new entries for missing provinces.".format(len(new_entries)))
print("Output written to {}.".format(output_path))