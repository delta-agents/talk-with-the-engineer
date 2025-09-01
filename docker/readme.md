# Docker

``` bash
cd /d "D:\my_projects\AI-agents-template"
docker build -t AI-agents-template/api:0.0.1 -f docker\Dockerfile .
docker run --name AI-agents-template_0.0.1 -p 8000:8000 -t AI-agents-template/api:0.0.1
```
