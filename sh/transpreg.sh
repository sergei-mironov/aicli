#!/bin/sh
# Draws a transparent region in the middle of an image

set -e

# Function to print usage
usage() {
  echo "Usage: $0 -r RATIO <input_image> <output_image>"
  exit 1
}

# Parse arguments
ratio=0.15  # default ratio
while getopts ":r:" opt; do
  case "$opt" in
    r) ratio="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND -1))

# Assign positional arguments to variables
image_path="$1"
outimage_path="$2"

# Ensure both input and output image paths are provided
if [ -z "$image_path" ] || [ -z "$outimage_path" ]; then
  usage
fi

# Get image dimensions
width=$(identify -format "%w" "$image_path")
height=$(identify -format "%h" "$image_path")

# Calculate the coordinates for the transparent rectangle
x1=$(echo "$width * $ratio" | bc)
y1=$(echo "$height * $ratio" | bc)
x2=$(echo "$width * (1.0 - $ratio)" | bc)
y2=$(echo "$height * (1.0 - $ratio)" | bc)

# Process the image using ImageMagick's convert
convert "$image_path" \
  -alpha set \
  \( +clone -alpha transparent -fill white -draw "rectangle $x1,$y1 $x2,$y2" \) \
  -compose DstOut -composite \
  "$outimage_path"

