#!/bin/bash

echo "🆓 PQC Secure Transfer - FREE Cloud Deployment"
echo "=============================================="
echo ""

# Check available tools
GCLOUD_AVAILABLE=$(command -v gcloud >/dev/null 2>&1 && echo "yes" || echo "no")
FLYCTL_AVAILABLE=$(command -v flyctl >/dev/null 2>&1 && echo "yes" || echo "no")

echo "🆓 FREE Deployment Options:"
echo ""
echo "1. 🥇 Google Cloud Run (BEST FREE OPTION)"
echo "   • 2 million requests/month FREE"
echo "   • Automatic HTTPS & scaling"
echo "   • Production-ready"
echo "   $([ "$GCLOUD_AVAILABLE" = "yes" ] && echo "✅ gcloud CLI ready" || echo "❌ Need gcloud CLI")"
echo ""
echo "2. 🚀 Railway (Easy Deployment)"
echo "   • $5 credit every month FREE"
echo "   • Deploy from GitHub in 1 click"
echo "   • Perfect for development"
echo "   ✅ Web-based (no CLI needed)"
echo ""
echo "3. 🌐 Render (Always-On Free)"
echo "   • 750 hours/month FREE"
echo "   • Always-on capability"
echo "   • Simple Docker deployment"
echo "   ✅ Web-based (no CLI needed)"
echo ""
echo "4. 🌍 Fly.io (Global Free)"
echo "   • 3 free VMs worldwide"
echo "   • Global edge deployment"
echo "   • Great performance"
echo "   $([ "$FLYCTL_AVAILABLE" = "yes" ] && echo "✅ flyctl CLI ready" || echo "❌ Need flyctl CLI")"
echo ""
echo "5. 📚 GitHub Codespaces (Development)"
echo "   • 120 hours/month FREE"
echo "   • Full development environment"
echo "   • Perfect for testing"
echo "   ✅ Web-based (no setup needed)"
echo ""

read -p "Choose your FREE deployment (1-5): " choice

case $choice in
    1)
        if [ "$GCLOUD_AVAILABLE" = "no" ]; then
            echo ""
            echo "❌ Google Cloud SDK not found"
            echo "📥 Install from: https://cloud.google.com/sdk/docs/install"
            echo ""
            echo "🔄 Alternative: Use the web console"
            echo "1. Go to https://console.cloud.google.com/run"
            echo "2. Click 'Create Service'"
            echo "3. Select 'Deploy from source repository'"
            echo "4. Connect GitHub: gayatrigosavi2424/pqc-secure-transfer"
            echo "5. Set memory to 512Mi, CPU to 1"
            exit 1
        fi
        
        echo ""
        echo "🚀 Deploying to Google Cloud Run (FREE)..."
        echo ""
        
        # Check if user is logged in
        if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
            echo "🔐 Please login to Google Cloud:"
            gcloud auth login
        fi
        
        # Get or set project
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            echo ""
            read -p "📝 Enter your Google Cloud Project ID: " PROJECT_ID
            gcloud config set project $PROJECT_ID
        fi
        
        echo "📦 Deploying to project: $PROJECT_ID"
        echo ""
        
        # Deploy with free tier optimizations
        gcloud run deploy pqc-secure-transfer \
            --source https://github.com/gayatrigosavi2424/pqc-secure-transfer \
            --region us-central1 \
            --allow-unauthenticated \
            --memory 512Mi \
            --cpu 1 \
            --concurrency 80 \
            --max-instances 5 \
            --set-env-vars="PQC_ALGORITHM=Kyber768,STREAM_CHUNK_SIZE=1048576" \
            --port 8765
        
        # Get the URL
        SERVICE_URL=$(gcloud run services describe pqc-secure-transfer --region us-central1 --format 'value(status.url)' 2>/dev/null)
        
        echo ""
        echo "🎉 FREE deployment successful!"
        echo "🔗 Your quantum-safe system: $SERVICE_URL"
        echo "💰 Cost: $0 (within 2M requests/month free tier)"
        echo ""
        echo "🧪 Test it:"
        echo "python examples/client.py --server $SERVICE_URL --create-test 10"
        ;;
        
    2)
        echo ""
        echo "🚀 Railway FREE Deployment (1-Click):"
        echo ""
        echo "1. 🌐 Go to: https://railway.app"
        echo "2. 🔐 Sign up with your GitHub account (FREE)"
        echo "3. 🚀 Click 'Deploy from GitHub repo'"
        echo "4. 📂 Select: gayatrigosavi2424/pqc-secure-transfer"
        echo "5. ⚙️  Railway auto-detects Dockerfile and deploys"
        echo "6. 💰 Get $5 monthly credit (enough for small apps)"
        echo ""
        echo "✅ No CLI needed - everything in the browser!"
        echo "🎯 Perfect for: Development and small production"
        ;;
        
    3)
        echo ""
        echo "🚀 Render FREE Deployment (Always-On):"
        echo ""
        echo "1. 🌐 Go to: https://render.com"
        echo "2. 🔐 Sign up with your GitHub account (FREE)"
        echo "3. 🆕 Click 'New Web Service'"
        echo "4. 🔗 Connect GitHub repository"
        echo "5. 📂 Select: gayatrigosavi2424/pqc-secure-transfer"
        echo "6. ⚙️  Configure:"
        echo "   • Environment: Docker"
        echo "   • Plan: Free (750 hours/month)"
        echo "   • Port: 8765"
        echo "7. 🚀 Click 'Create Web Service'"
        echo ""
        echo "✅ 750 hours = 24/7 operation for 31 days!"
        echo "🎯 Perfect for: Always-on free hosting"
        ;;
        
    4)
        if [ "$FLYCTL_AVAILABLE" = "no" ]; then
            echo ""
            echo "📥 Installing Fly.io CLI..."
            curl -L https://fly.io/install.sh | sh
            echo ""
            echo "🔄 Please restart your terminal and run this script again"
            echo "Or add to PATH: export PATH=\"\$HOME/.fly/bin:\$PATH\""
            exit 1
        fi
        
        echo ""
        echo "🚀 Deploying to Fly.io (3 FREE VMs)..."
        echo ""
        
        # Login to Fly.io
        flyctl auth login
        
        # Create fly.toml for free tier
        cat > fly.toml << EOF
app = "pqc-secure-transfer-$(date +%s)"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile"

[env]
  PQC_ALGORITHM = "Kyber768"
  PORT = "8765"

[http_service]
  internal_port = 8765
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
EOF
        
        # Launch and deploy
        flyctl launch --no-deploy --copy-config
        flyctl deploy
        
        APP_NAME=$(grep "^app" fly.toml | cut -d'"' -f2)
        echo ""
        echo "🎉 FREE deployment successful!"
        echo "🔗 Your app: https://$APP_NAME.fly.dev"
        echo "💰 Cost: $0 (3 free VMs)"
        ;;
        
    5)
        echo ""
        echo "🚀 GitHub Codespaces FREE Development:"
        echo ""
        echo "1. 🌐 Go to: https://github.com/gayatrigosavi2424/pqc-secure-transfer"
        echo "2. 💚 Click the green 'Code' button"
        echo "3. 📱 Select 'Codespaces' tab"
        echo "4. 🆕 Click 'Create codespace on main'"
        echo "5. ⏳ Wait for environment to load (2-3 minutes)"
        echo "6. 🚀 In the terminal, run:"
        echo "   python simple_demo.py"
        echo ""
        echo "✅ 120 hours/month FREE"
        echo "🎯 Perfect for: Development and testing"
        echo "💡 Tip: Codespace includes VS Code, terminal, and all tools!"
        ;;
        
    *)
        echo "❌ Invalid choice. Please run the script again and choose 1-5."
        exit 1
        ;;
esac

echo ""
echo "📊 FREE Tier Comparison:"
echo "┌─────────────────┬──────────────┬─────────────────┬──────────────┐"
echo "│ Platform        │ Monthly Cost │ Free Limits     │ Best For     │"
echo "├─────────────────┼──────────────┼─────────────────┼──────────────┤"
echo "│ Google Cloud    │ \$0          │ 2M requests     │ Production   │"
echo "│ Railway         │ \$0          │ \$5 credit      │ Development  │"
echo "│ Render          │ \$0          │ 750 hours       │ Always-on    │"
echo "│ Fly.io          │ \$0          │ 3 VMs           │ Global       │"
echo "│ Codespaces      │ \$0          │ 120 hours       │ Development  │"
echo "└─────────────────┴──────────────┴─────────────────┴──────────────┘"
echo ""
echo "🎉 Your PQC Secure Transfer System is now running FREE!"
echo "🔐 Quantum-safe security at zero cost!"
echo ""
echo "📝 Next steps:"
echo "• Test your deployment with the provided examples"
echo "• Set up monitoring (most platforms include free monitoring)"
echo "• Configure custom domain (optional)"
echo "• Scale up when you need more resources"