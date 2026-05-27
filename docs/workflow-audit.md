# n8n Workflow Audit

## 1. Existing Workflows
- `AI Powered Document Assistant - Knowledge Base.json`
- `DP Job Application - ChatBot.json`

## 2. Analysis
- **AI Powered Document Assistant**: A robust RAG pipeline syncing Google Drive docs into a Pinecone vector store on a cron schedule. Contains a Telegram bot to chat with the knowledge base. This is fairly complete but could use an improved chat model in the future.
- **DP Job Application - ChatBot**: A simple Telegram bot that uses a Gemini 2.5 Flash model and Notion tools to track job applications. It uses simple memory and Tavily for web search.

## 3. Planned Enhancement (Day 7)
- **Target Workflow**: `DP Job Application - ChatBot.json`
- **Enhancement**: Swap the existing Gemini 2.5 Flash model for a Claude 3 Haiku / Anthropic model (or update the existing AI node configuration to include a more advanced model like Gemini 1.5 Pro) to provide better reasoning capabilities for the agent. I will update the JSON to use an Anthropic Chat Model node.

