# Azure Platform Architecture Design
![azure architecture diagram](./Catalyst%20NextGen%20Architecture%20Design.drawio.png)

# Dataflow
1. User browses to the app and authenticates using Entra ID credentials.
1. Backend API fetches a list of User Projects from the CosmosDB database. A user chooses to continue working with an existing User Project or create a new one.
1. Template Workflows and user-created Curated Workflows are persisted to the Microsoft Foundry project by the backend API.
1. Agents created for single-use or for inclusion within Multi-agent workflows are persisted to the Microsoft Foundry project by the backend API.
1. AI Model deployments used by Agents and Workflows are configured within the Microsoft Foundry project. These are created using the Foundry Portal or Infrastructure-as-Code provisioning templates.
1. Addtional API capabilities and Skills (Tools) are available via Model Context Protocol (MCP) connections. 


# Provisioned Resources
1. Microsoft Foundry Account and Foundry Project
1. App Service and App Service Environment
1. CosmosDB Account and Database
1. Azure Blob Storage Account and Container
1. Azure Log Analytics Workspace
1. Azure Application Insights
1. Azure Key Vault

Infrastructure as Code (IaC) templates are used to represent current state of provisioned resources and to make them easily re-deployable. Azure Verfified Modules include both Bicep and Terreform templates for all needed resources.

## Microsoft Foundry Account and Foundry Project
Agents and Workflows are persisted to a single Foundry Project within Microsoft Foundry. All Agents, Workflows, and Model deployments in the system are contained within this single project for ease of administration and monitoring.

## App Service and App Service Environment
App Service is used to host the frontend app (ReactJS) along with the backend API that represents the orchestration layer of the Catalyst NextGen app.

## CosmosDB Account and Database
CosmosDB is used to store all of the metadata related to user Projects and operational data for the app. A single database provisioned with the Serverless SKU is sufficient for MVP and testing phases. Production phase should consider provisioned RU/s with multi-region read capabilities enabled for resiliency.

## Azure Blob Storage Account and Container
A blob storage container is used to store any working source documents and generated output documents for a given project. Metadata for these items are stored in the operational CosmosDB database for the app.

## Azure Log Analytics Workspace
A log analytics workspace is used to capture monitoring, metrics, and application telemtry data. Microsoft Foundry natively uses this as the source for operational dashboards.

## Azure Application Insights
Microsoft Foundry Agents and Workflows require an instance of Application Insights to capture open-telemetry and observability data. This data is stored within the Log Analytics workspace and surfaced in Azure Monitor or from the Foundry Portal Operations center.

## Azure Key Vault
Key Vault is used to persist sensitive configuration data such as API access keys and connection strings. Values will be read at build and deployment time from Azure DevOps pipelines to inject values for the correct environment into the application's configuration.