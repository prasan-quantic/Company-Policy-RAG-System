web: gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Check imports
      run: |
        python -c "import flask; print('Flask OK')"
        python -c "import chromadb; print('ChromaDB OK')"
        python -c "import sentence_transformers; print('Sentence Transformers OK')"

    - name: Validate app structure
      run: |
        python -c "import app; print('App imports successfully')"
        python -c "import rag; print('RAG module OK')"
        python -c "import ingest; print('Ingest module OK')"

    - name: Check document corpus
      run: |
        python -c "import os; docs = os.listdir('documents'); print(f'Found {len(docs)} documents'); assert len(docs) >= 8, 'Missing documents'"

    - name: Test document ingestion (dry run)
      run: |
        python -c "from ingest import DocumentIngestion; ing = DocumentIngestion(); print('Ingestion module initialized successfully')"

    - name: Lint code (optional)
      continue-on-error: true
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Deploy to Render
      if: ${{ secrets.RENDER_DEPLOY_HOOK }}
      run: |
        curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}

    - name: Deploy to Railway
      if: ${{ secrets.RAILWAY_TOKEN }}
      uses: bervProject/railway-deploy@main
      with:
        railway_token: ${{ secrets.RAILWAY_TOKEN }}
        service: company-policy-rag

    - name: Wait for deployment
      run: sleep 30

    - name: Health check
      if: ${{ secrets.APP_URL }}
      run: |
        response=$(curl -s -o /dev/null -w "%{http_code}" ${{ secrets.APP_URL }}/health)
        if [ $response -eq 200 ]; then
          echo "✅ Deployment successful! Health check passed."
        else
          echo "❌ Health check failed with status $response"
          exit 1
        fi
