# Docker

``` bash
cd /d "D:\my_projects\talk-with-the-engineer"
docker build -t talk-with-the-engineer/api:0.0.1 -f docker\Dockerfile .
docker run --name talk-with-the-engineer_0.0.1 -p 8000:8000 -t talk-with-the-engineer/api:0.0.1
```
