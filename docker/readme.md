# Docker

``` bash
cd /d "D:\my_projects\skip-the-engineer"
docker build -t skip-the-engineer/api:0.0.1 -f docker\Dockerfile .
docker run --name skip-the-engineer_0.0.1 -p 8000:8000 -t skip-the-engineer/api:0.0.1
```
