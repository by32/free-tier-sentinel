# 📦 Project Brief: Multi-Cloud Free-Tier Planner with Live Capacity & Provisioning-Retry

## 🚀 Executive Summary

We are building a toolchain to help users launch **cloud resources that stay within free-tier or promotional credit constraints** while avoiding provisioning failures due to regional capacity limitations. This includes:

- An **open-source constraint database** of quota and free-tier limits across AWS, GCP, Azure, and OCI.
- A **Python-based planner** that uses integer linear programming (`pulp`) to find a valid, cost-free plan.
- A **live capacity detection layer** that prevents the planner from recommending shapes that are temporarily unavailable.
- A **provisioning-retry engine** that repeatedly attempts launch steps until they succeed or time out.

...

### 📇 Contact

- **Product Lead:** [Your Name]  
- **Technical Lead:** [Tech Lead]  
- **Repository (pending):** `https://github.com/<org>/cloud-free-constraints`

--- 
