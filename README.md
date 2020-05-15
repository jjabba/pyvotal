# Pyvotal
Python 3 lib for easy access to pivotal tracker's APIv5

### Installation
Install using pip

     python3 -m pip install pyvotal5

### Example
List all epics in all projects

     from pyvotal5.pyvotal import set_token, Project
     set_token('yOuRsEcReTtOk3n')
     for p in Project.fetch_all():
          for e in p.epics:
              print(e.name)
