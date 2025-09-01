# Skip the engineer

This package contains core functionality for a Skip the engineer package, developed to showcase and speed up the process of developing a Skip the engineer. This Skip the engineer template is developed by HKV and is published under the GNU GPL-3 license.

<details>
<summary>Project structure</summary>

## Project structure

THis project is structured to include multiple agents in one repository. In case you only want one agent, you can remove the sub folders in tools and only use one agent and router.

### Agents

These contain the agents themselves. If you only plan to use MCP you can forget about the agents. Can be useful to debug and test during development.

### Models

This repository is structured specifically to work well with `pydantic-ai`.
The `Pydantic` in package is a framework which uses models.
Every tool which the agents has access to uses an input and output model.
This helps structuring the code and helps ensuring the correct data is passed to and from the tools by the agent.
In turn it hels the LLM you use to better understand what the tools do and how to use them.
If models are used by other models, these can be placed in the `base.py` to be used in several other files.

### Routers

This allows the tools to be accessible through fast-api and fast-mcp endpoints. `setup_connections.py` handles generic initialization needed by all the tools.

### Tools

These are the tool themselves. Each tool has its own file to keep the project manageable.

### Utils

These are functions called by the tools but are generic and can be used by multiple tools. Good practice to split these from the tools themselves.
</details>

## Developing

Here are a couple quick useful things to know when using this repo.

### Pre-commit

This repo uses pre-commit, make sure you run `pixi run pre-commit` before you commit anything.

### GitHub Tests

In the folder `.github` there are four workflows which run automatically when submitting a pull request.

### Pixi

Read bellow for more information on pixi and a quick guideline you can include in your project.

## Getting started

### Using install

run `pip install skip_the_engineer`

### developing with pixi

To manage the environment we use Pixi.

<details>
<summary>windows</summary>

```powershell
iwr -useb https://pixi.sh/install.ps1 | iex
```

</details>

<details>
<summary>Linux/Mac</summary>

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

</details>

#### installing

With the `Pixi` command in powershell install the python environment:

```bash
 cd ../skip_the_engineer
 pixi install
```

The `pixi.lock` file loads the correct packages and downloads to the `.pixi` folder.

For questions about how to use this package contact `hoek@hkv.nl` or `haasnoot@hkv.nl`.
