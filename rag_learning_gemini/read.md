RAG Architecture Explorer & Debugger

Installation sequence
  a.  Set up an OCP Cluster with a GPU node
  b.  Install MinIO-based object storage
  c.  Install necessary Operators and RHOAI
  d.  Set up VectorDB with ChromaDB
  e.  Run OpenShift image build for API, UI, and ingestion. Ensure using RAG-Learning as namespace
  f.  Deploy the apps in sequence - API-->UI-->Ingestion


  ##Command for running BuildConfig and Build

oc new-build --binary --name=api --strategy=docker -n ai-stack-dev
oc start-build api --from-dir=apps/api --follow -n ai-stack-dev
