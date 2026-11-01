set -euo pipefail

# --- Configuration ---
# Set the base directory containing all 131 SQL files
BASE_QUERY_DIR="$HOME/tpcds_queries_spark"
# Define the number of subfolders you want to create
NUM_FOLDERS=5

echo "Starting query file splitting setup..."
echo "Source directory: $BASE_QUERY_DIR"

# 1. Check if the source directory exists
if [ ! -d "$BASE_QUERY_DIR" ]; then
    echo "ERROR: Source query directory not found at $BASE_QUERY_DIR"
    exit 1
fi

# 2. Create the 5 subdirectories (e.g., /part1, /part2, ...)
for i in $(seq 1 $NUM_FOLDERS); do
    SUB_DIR="$BASE_QUERY_DIR/part$i"
    mkdir -p "$SUB_DIR"
    echo "Created folder: $SUB_DIR"
done

# 3. Find and sort all query files numerically (Handles non-zero-padding)
# We use 'sort -V' (version sort) to get 1.sql before 10.sql
# We skip the "part" folders we just created by filtering for files only
QUERY_FILES=$(find "$BASE_QUERY_DIR" -maxdepth 1 -type f -name "*.sql" | sort -V)

# 4. Count the total number of queries
TOTAL_QUERIES=$(echo "$QUERY_FILES" | wc -l)
if [ "$TOTAL_QUERIES" -lt 131 ]; then
    echo "WARNING: Found only $TOTAL_QUERIES queries. Expected 131."
fi

# Calculate how many queries go into each folder (roughly)
QUERIES_PER_FOLDER=$((TOTAL_QUERIES / NUM_FOLDERS))
CURRENT_COUNT=0
CURRENT_FOLDER=1

echo "Total queries found: $TOTAL_QUERIES. Distributing into $NUM_FOLDERS parts..."

# 5. Loop through the sorted queries and move them into the parts
echo "$QUERY_FILES" | while read -r file_path; do
    if [ -z "$file_path" ]; then
        continue
    fi
    
    FILE_NAME=$(basename "$file_path")
    
    # Define the destination directory for the current file
    DEST_DIR="$BASE_QUERY_DIR/part$CURRENT_FOLDER"
    
    # Move the file
    mv "$file_path" "$DEST_DIR/$FILE_NAME"

    CURRENT_COUNT=$((CURRENT_COUNT + 1))

    # Check if we should switch to the next folder
    # Also ensure we don't switch folders if we are on the last one
    if [ "$CURRENT_FOLDER" -lt "$NUM_FOLDERS" ] && [ "$CURRENT_COUNT" -ge "$QUERIES_PER_FOLDER" ]; then
        echo "Moved $CURRENT_COUNT queries to part$CURRENT_FOLDER."
        CURRENT_FOLDER=$((CURRENT_FOLDER + 1))
        CURRENT_COUNT=0
    fi
done

echo "Query distribution complete. Files are now in $BASE_QUERY_DIR/part[1-5]"
