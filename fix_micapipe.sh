#!/bin/bash

# Fix script for micapipe snakenull plugin
# Run this on your server where micapipe is located

echo "=== Micapipe Snakenull Plugin Fix ==="
echo ""

# Check current setup
echo "1. Checking current snakebids installation:"
cd /home/bic/eyang/Documents/micapipe/micapipe_snakebids
python -c "import snakebids; print('Current snakebids:', snakebids.__file__)"

echo ""
echo "2. Checking if snakenull plugin exists:"
python -c "
try:
    from snakebids.plugins.snakenull import generate_inputs_with_snakenull
    print('✓ Plugin found')

    import inspect
    source = inspect.getsource(generate_inputs_with_snakenull)
    if '_collect_files_manually' in source:
        print('✓ Plugin has normalization code - should work!')
    else:
        print('✗ Plugin is OLD version - needs update!')
        print('Snakenull count:', source.count('snakenull'))
except ImportError as e:
    print('✗ Plugin not found:', e)
"

echo ""
echo "3. If plugin is old, here are your options:"
echo ""
echo "OPTION 1: Update the snakebids installation at:"
echo "  /home/bic/eyang/Documents/snakebids"
echo "  (Copy the fixed plugin file there)"
echo ""
echo "OPTION 2: Clone and use the fixed version:"
echo "  cd /home/bic/eyang/Documents/"
echo "  git clone https://github.com/zihuaihuai/snakebids.git snakebids-fixed"
echo "  cd snakebids-fixed"
echo "  git checkout plugin"
echo "  pip install -e ."
echo ""
echo "OPTION 3: Download just the fixed plugin file:"
echo "  wget https://raw.githubusercontent.com/zihuaihuai/snakebids/plugin/snakebids/plugins/snakenull.py"
echo "  cp snakenull.py /home/bic/eyang/Documents/snakebids/snakebids/plugins/"
echo ""

echo "=== Test command after fix ==="
echo "python -c \"
from snakebids.plugins.snakenull import generate_inputs_with_snakenull
import inspect
source = inspect.getsource(generate_inputs_with_snakenull)
if '_collect_files_manually' in source:
    print('✅ Fixed plugin is working!')
else:
    print('❌ Still using old plugin')
\""
