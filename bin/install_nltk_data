# bin/install_nltk_data
#!/usr/bin/env bash

source $BIN_DIR/utils

echo "-----> Starting nltk data installation"

python -m nltk.downloader averaged_perceptron_tagger
python -m nltk.downloader wordnet

# Open the NLTK_DATA directory
cd ${NLTK_DATA}

# Delete all of the zip files
find . -name "*.zip" -type f -delete

echo "-----> Finished nltk data installation"