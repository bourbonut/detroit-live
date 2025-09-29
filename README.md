# detroit-live

`detroit-live` is based on [`detroit`](https://github.com/bourbonut/detroit) and aims to bring interactivity to visualizations.

# Installation

```sh
pip install git+https://github.com/bourbonut/detroit-live.git
```

# Coverage

| Package Name    | Yes / No | Tests OK | Notes                           |
|-----------------|----------|----------|---------------------------------|
| brush           | No       | -        |                                 |
| dispatch        | Yes      | Yes      |                                 |
| drag            | Yes      | Yes      | Touch events not tested         |
| selection       | Yes      | Yes      |                                 |
| timer           | Yes      | Yes      |                                 |
| transition      | No       | -        |                                 |
| zoom            | Yes      | Yes      | Touch events not tested         |


## Examples

```shell
pip install git+https://github.com/bourbonut/detroit-live.git
python examples/heatmap.py
python examples/rainbow_circles.py
python examples/index_chart.py
python examples/quadtree_find_circle.py
```
