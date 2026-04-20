# gke-sample-app

A simple calculator web app for learning Kubernetes on GKE, containerisation with Docker, and keyless CI/CD with GitHub Actions and Workload Identity Federation.

This app is deployed onto the GCP infrastructure provisioned by [Terraform-learning](../Terraform-learning).

## What this project teaches

| Concept | Where |
|---|---|
| Containerising a Python app | `Dockerfile` |
| Production WSGI server (gunicorn) | `Dockerfile`, `app/requirements.txt` |
| Kubernetes Deployments and rolling updates | `k8s/deployment.yaml` |
| Kubernetes Services and NodePort | `k8s/service.yaml` |
| Liveness and readiness probes | `k8s/deployment.yaml`, `app/app.py` |
| GitHub Actions CI/CD pipeline | `.github/workflows/ci-cd.yml` |
| Keyless GCP auth (Workload Identity Federation) | `.github/workflows/ci-cd.yml` |
| Pushing images to GCR | CI/CD pipeline |
| Rolling deployments with SHA-tagged images | CI/CD pipeline |

---

## Architecture

```
  Developer
  git push main
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  GitHub Actions                                                  │
  │                                                                  │
  │  Job: test ──────────────────────────────────────────────────┐  │
  │    pytest tests/ -v                                           │  │
  │                                                               │  │
  │  Job: build  (needs: test)  ──────────────────────────────┐  │  │
  │    1. Request GitHub OIDC token                            │  │  │
  │    2. Exchange token with GCP STS (Workload Identity)      │  │  │
  │    3. docker build                                          │  │  │
  │    4. docker push gcr.io/<project>/calculator:sha-<abc>    │  │  │
  │                                                            │  │  │
  │  Job: deploy (needs: build) ──────────────────────────┐   │  │  │
  │    1. Authenticate to GCP via WIF                      │   │  │  │
  │    2. gcloud → kubeconfig                              │   │  │  │
  │    3. kubectl apply -f k8s/                            │   │  │  │
  │    4. kubectl set image → rolling update               │   │  │  │
  │    5. kubectl rollout status (wait for healthy)        │   │  │  │
  └────────────────────────────────────────────────────────┘───┘──┘──┘
                          │ deploy
                          ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  GCP (provisioned by Terraform-learning/)                        │
  │                                                                  │
  │  GCR  gcr.io/<project>/calculator                               │
  │    stores versioned Docker images (one per Git SHA)             │
  │                              │ pull on deploy                   │
  │                              ▼                                  │
  │  GKE Cluster  (regional, 3 zones)                               │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │  Deployment: calculator  (2 replicas)                    │   │
  │  │  ┌──────────────────┐   ┌──────────────────┐            │   │
  │  │  │ Pod  port 8080   │   │ Pod  port 8080   │            │   │
  │  │  │ (gunicorn/Flask) │   │ (gunicorn/Flask) │            │   │
  │  │  └──────────────────┘   └──────────────────┘            │   │
  │  │                                                          │   │
  │  │  Service: NodePort 30080 ─────────────────────────────► │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │                              ▲                                  │
  │  Global HTTP Load Balancer   │  routes to NodePort 30080        │
  │  (static anycast IP)  ───────┘                                  │
  └─────────────────────────────────────────────────────────────────┘
                          ▲
                      Internet
                    (HTTP port 80)
```

---

## Workload Identity Federation — how keyless auth works

No service account key is stored anywhere. GitHub Actions gets a short-lived GCP token at runtime:

```
GitHub Actions runner
  │
  │  1. Requests a signed OIDC token from GitHub
  │     Token contains: repository, actor, branch, SHA
  │
  ▼
GCP Security Token Service (STS)
  │  2. Verifies token is signed by GitHub's OIDC issuer
  │  3. Checks attribute_condition:
  │       assertion.repository == "your-username/gke-sample-app"
  │     (rejects forks and unrelated repos)
  │  4. Returns a federated identity token
  │
  ▼
GCP IAM
  │  5. Exchanges federated token for a short-lived SA access token
  │     scoped to: github-actions-cicd@<project>.iam.gserviceaccount.com
  │
  ▼
GitHub Actions runner now has a GCP token that expires when the job ends.
No key file. Nothing to rotate. Nothing to leak.
```

---

## Project structure

```
gke-sample-app/
├── app/
│   ├── app.py                  # Flask calculator — routes, logic, /healthz
│   ├── requirements.txt        # Flask + gunicorn (pinned versions)
│   └── templates/
│       └── index.html          # Jinja2 HTML UI
├── tests/
│   └── test_app.py             # pytest unit tests (10 test cases)
├── k8s/
│   ├── deployment.yaml         # 2 replicas, rolling update, liveness/readiness probes
│   └── service.yaml            # NodePort 30080 → pod port 8080
├── .github/
│   └── workflows/
│       └── ci-cd.yml           # test → build (GCR) → deploy (GKE) via WIF
└── Dockerfile                  # python:3.12-slim, gunicorn entrypoint
```

---

## Setup

### Prerequisites

The GCP infrastructure must be provisioned first. See [Terraform-learning](../Terraform-learning) and run `terraform apply` in `environments/dev/`.

### 1. Update the image name in deployment.yaml

In [k8s/deployment.yaml](k8s/deployment.yaml), replace the placeholder with your actual GCP project ID:

```yaml
image: gcr.io/your-gcp-project-id/calculator:latest
```

Or get the exact value from Terraform:
```bash
cd ../Terraform-learning/environments/dev
terraform output -raw cicd_gcr_registry_url
# Output: gcr.io/your-project-id
# Use: gcr.io/your-project-id/calculator:latest
```

### 2. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Where to get the value |
|---|---|
| `GCP_PROJECT_ID` | your GCP project ID |
| `WIF_PROVIDER` | `terraform output -raw cicd_wif_provider` |
| `WIF_SERVICE_ACCOUNT` | `terraform output -raw cicd_wif_service_account` |
| `GKE_CLUSTER_NAME` | e.g. `dev-gke-cluster` (your `cluster_name` tfvar) |
| `GKE_CLUSTER_ZONE` | e.g. `us-central1` (your `region` tfvar) |

### 3. Update `github_repo` in Terraform

In [Terraform-learning/environments/dev/terraform.tfvars](../Terraform-learning/environments/dev/terraform.tfvars):

```hcl
github_repo = "your-github-username/gke-sample-app"
```

Then re-run `terraform apply` to update the WIF attribute condition.

### 4. First-time manual deploy

The CI/CD pipeline deploys on every push, but you need to bootstrap the Kubernetes resources once:

```bash
# Configure kubectl to talk to your GKE cluster
gcloud container clusters get-credentials dev-gke-cluster \
  --region us-central1 --project YOUR_PROJECT_ID

# Create the Deployment and Service
kubectl apply -f k8s/

# Verify pods are running
kubectl get pods
kubectl get service calculator
```

After this, all future deployments happen automatically via GitHub Actions.

### 5. Push to trigger the pipeline

```bash
git add .
git commit -m "initial deploy"
git push origin main
```

Watch the pipeline at: `https://github.com/your-username/gke-sample-app/actions`

---

## CI/CD pipeline jobs

```
On push to main:

  [test]  ──────────────────────────────────────────────── runs on every push & PR
    • pip install Flask gunicorn pytest
    • pytest tests/ -v
    • fails fast before any image is built

  [build]  (needs: test, push only) ────────────────────── skipped on PRs
    • Authenticate to GCP via Workload Identity Federation
    • gcloud auth configure-docker
    • docker build -t gcr.io/<project>/calculator:sha-<abc> .
    • docker push (two tags: SHA + latest)
    • Build cache stored in GitHub Actions cache (faster rebuilds)

  [deploy]  (needs: build) ─────────────────────────────── skipped on PRs
    • Authenticate to GCP via WIF
    • gcloud → kubeconfig (fresh every job)
    • kubectl apply -f k8s/        (idempotent — safe to run always)
    • kubectl set image deployment/calculator calculator=<sha-tagged-image>
    • kubectl rollout status       (waits up to 120s; fails job if unhealthy)
```

**Every image is tagged with its Git SHA.** If a deployment breaks, you can roll back to any previous commit's image:
```bash
kubectl rollout undo deployment/calculator
# or to a specific revision:
kubectl rollout history deployment/calculator
kubectl rollout undo deployment/calculator --to-revision=3
```

---

## Running locally

```bash
# Install dependencies
pip install -r app/requirements.txt

# Start the app
python app/app.py
# Visit http://localhost:8080

# Run tests
pip install pytest
pytest tests/ -v
```

## Running with Docker

```bash
docker build -t calculator:latest .
docker run -p 8080:8080 calculator:latest
# Visit http://localhost:8080
```

---

## Useful kubectl commands

```bash
# Watch all pods in real time
kubectl get pods -w

# Stream logs from all calculator pods
kubectl logs -l app=calculator --follow

# Check rollout history
kubectl rollout history deployment/calculator

# Roll back to the previous version
kubectl rollout undo deployment/calculator

# Describe a pod (useful for debugging image pull or probe failures)
kubectl describe pod -l app=calculator

# Check the Service endpoints (confirms pods are registered as healthy)
kubectl get endpoints calculator
```

---

## Companion project

**[Terraform-learning](../Terraform-learning)** — provisions all GCP infrastructure this app runs on: VPC, GKE cluster, Global Load Balancer, GCR registry, CI/CD service account, and Workload Identity Federation.
