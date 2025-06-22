# PSVN
公司使用svn还要写更新文档，遂写此工具，还在逐步更新中
# How To Use
python == 3.13.3
```bash
psvn.py [-h] [-p PATH] [-i IGNORE] [-s SUBPRJ] [-t TYPE]
```
## example
```bash
# 设置ignored
python psvn.py -p /path/to/your/repo -i Debug,dist
# 打印diff
python psvn.py -p /path/to/your/repo

```
