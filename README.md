# Panda3D scene builder #
A simple tool developed using Panda3D which allows a user to create a scene using his/her own models.

# Setup #

## Install the deps ##

```
pip install -r requirements.txt
```

## Configure the application ##
The configuration file (config/scene\_builder.json) is a simple json file which contains 2 keys:

 * base\_model: the path to the room/terrain model used as a base for the scene
 * props: a list of scene props(single-keyed dictionaries) defined in a similar way.

NOTE: both the scene base\_model and the props MUST be in .egg format(for the time being).\
NOTE2: the props MUST contain a group called "Collider" containing the "\<Collide\> \{ Polyset keep descend \}" tag. Otherwise, they will not be loaded.\

## Run ##
```
python scene_builder.py
```

## Export ##
You can export the scene you have created using Ctrl + e. It will be saved as "export/scene.json". The generated json will be very similar to the configuration one. It should be easy to figure out how to use it in your application 
