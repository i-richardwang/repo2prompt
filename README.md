# GitSeek

🔍 A backend service that helps you find the exact code you need from any Git repository using natural language queries, transforms the filtered content into prompt-friendly format for LLMs, and generates system architecture diagrams automatically.

> This project is inspired by and heavily references [GitIngest](https://github.com/cyclotruc/gitingest). While maintaining the core concept of repository content extraction, I've made three main changes:
> 1. Added Large Language Models for natural language understanding
> 2. Adapted the architecture to use the LangGraph framework
> 3. Restructured as a backend-only service with RESTful APIs

## 🚀 Features

- **Natural Language Code Finding**: Simply describe what code you want to find or exclude in plain English
- **Smart Code Filtering**: LLM understands your needs and automatically figures out which files to include or exclude
- **Context-Aware Search**: Takes into account both your description and the repository structure
- **Automated Architecture Diagram**: Generates system design diagrams based on repository analysis
- **Advanced Processing Pipeline**:
  - Smart repository structure analysis
  - Natural language understanding
  - Intelligent code filtering
  - Clean result extraction
  - System architecture visualization
- **RESTful API**: Easy integration with other services
- **Flexible Configuration**: Customizable file size limits and filtering options

## 🏗️ Architecture

The project is built using a state machine workflow powered by LangGraph, consisting of the following nodes:

```mermaid
%%{init: {'flowchart': {'curve': 'linear'}}}%%
graph TD;
    __start__([<p>Start</p>]):::first
    fetch_repo(Fetch Repository Content)
    analyze_structure(Analyze Code Structure)
    check_query(Check User Query)
    check_diagram(Check Diagram Setting)
    generate_filters(Generate LLM-Based Filters)
    extract_content(Extract Relevant Code)
    generate_diagram(Generate Architecture Diagram)
    cleanup(Cleanup Resources)
    __end__([<p>End</p>]):::last

    __start__ --> fetch_repo;
    fetch_repo --> analyze_structure;
    analyze_structure --> check_query;
    analyze_structure --> check_diagram;
    check_query -. Has natural language query .-> generate_filters;
    check_query -. Has predefined filters .-> extract_content;
    check_diagram -. Diagram enabled .-> generate_diagram;
    check_diagram -. Diagram disabled .-> extract_content;
    generate_filters --> extract_content;
    extract_content --> cleanup;
    generate_diagram --> cleanup;
    cleanup --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

Each node serves a specific purpose:

1. **Fetch Repository Content**: Clone and prepare the target repository
2. **Analyze Code Structure**: Scan and understand the repository structure
3. **Check User Query**: Determine if natural language processing is needed
4. **Check Diagram Setting**: Determine if diagram generation is enabled
5. **Generate LLM-Based Filters**: Convert natural language to code filters
6. **Extract Relevant Code**: Apply filters and extract matching content
7. **Generate Architecture Diagram**: Create system design visualization (parallel to content extraction)
8. **Cleanup Resources**: Clean up temporary files and resources

## 🛠️ Tech Stack

- **FastAPI**: Modern web framework for building APIs
- **LangGraph**: State machine workflow framework
- **LangChain**: LLM integration and chain management
- **Git**: Repository management
- **Pydantic**: Data validation and settings management
- **Mermaid.js**: System architecture diagram generation

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Starting the Server

```bash
uvicorn src.main:app --reload-include "src/**/*"
```

### API Endpoint

```bash
POST /api/analyze
```

Request body:
```json
{
    "url": "https://github.com/username/repo",
    "query": "I want to get the code that is related to the user authentication",
    "enable_diagram": true
}
```

## 🌟 Key Features and Differences

1. **LangGraph Integration**: Implemented a state machine workflow for more complex processing
2. **LLM Capabilities**: Added intelligent pattern generation and content analysis
3. **Architecture Visualization**: Automatic generation of system design diagrams
4. **Enhanced Processing**: More sophisticated repository analysis and content processing
5. **Modular Architecture**: Better separation of concerns and extensibility
6. **API-First Design**: Focus on programmatic access and integration

## 🔧 Development

1. Clone the repository
```bash
git clone https://github.com/yourusername/gitseek.git
cd gitseek
```

2. Install development dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.