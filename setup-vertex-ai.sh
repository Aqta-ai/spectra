#!/bin/bash

echo "🔧 Setting up Vertex AI for Spectra..."
echo ""

# Step 1: Authenticate with Google Cloud
echo "Step 1: Authenticating with Google Cloud..."
echo "This will open a browser window for authentication."
gcloud auth application-default login

# Step 2: Set the project
echo ""
echo "Step 2: Setting project to analog-sum-485815-j3..."
gcloud config set project analog-sum-485815-j3

# Step 3: Enable required APIs
echo ""
echo "Step 3: Enabling required APIs..."
gcloud services enable aiplatform.googleapis.com
gcloud services enable generativelanguage.googleapis.com

# Step 4: Verify authentication
echo ""
echo "Step 4: Verifying authentication..."
gcloud auth application-default print-access-token > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Authentication successful!"
else
    echo "❌ Authentication failed. Please try again."
    exit 1
fi

echo ""
echo "✅ Vertex AI setup complete!"
echo ""
echo "Next steps:"
echo "1. Run: ./run.sh"
echo "2. Open: http://localhost:3000"
echo "3. Press W to share your screen"
echo "4. Say 'Hey Spectra' to begin"
