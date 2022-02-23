from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import PandaNode, NodePath, Camera, TextNode, CollisionRay, CollisionHandlerQueue, CollisionTraverser, CollisionNode, CollideMask, CollisionSphere, CollisionHandlerPusher, BitMask32, Vec3, Vec2
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectButton import DirectButton 
from direct.gui.DirectOptionMenu import DirectOptionMenu
from direct.task.Timer import Timer
from panda3d.core import LPoint3f

import os
import json
import copy

MOVE_MODE = 1
ROTATE_MODE = 2

class SceneBuilder(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.win.setClearColor((0,1,1,0))
        self.disableMouse()

        self.camera.setPos(0,0,2)

        self.cTrav = CollisionTraverser()
        self.cQueue = CollisionHandlerQueue()
        self.pickerNode = CollisionNode('mouseRay')
        self.pickerNP = camera.attachNewNode(self.pickerNode)
        self.pickerNode.setFromCollideMask(BitMask32.bit(1))
        self.pickerRay = CollisionRay()
        self.pickerNode.addSolid(self.pickerRay)
        self.cTrav.addCollider(self.pickerNP,self.cQueue)

        self.dragging = False
        self.dragMod = False
        self.selected = None
        self.lastSelected = None
        self.tmpTextTimer = None 
        self.rotating = False
        self.mode = MOVE_MODE

        self.mousePosForRot = Vec2(0,0)

        self.keyMapping = {
            'forward': False,
            'backwards': False,
            'left': False,
            'right': False,
            'rot-up': False,
            'rot-down': False,
            'rot-left': False, 
            'rot-right': False, 
            'delete': False
        }

        cfg_json = open('config/scene_builder.json',"r")
        cfg = json.loads(cfg_json.read())
        cfg_json.close()
        
        #base
        self.environ = loader.loadModel(cfg['base_model'])
        self.environ.reparentTo(render)

        #props
        self.props = {}
        self.propNames = []
        for p in cfg['props']:
            prop = loader.loadModel(p['model'])
            collider = prop.find('**/Collider')
            collider.name = str(p['model']) + '__Collider'
            if collider.isEmpty():
                print('Skipping ' + p['model'] + ': collider is missing')
            else:
                self.cTrav.addCollider(collider,self.cQueue)
                name = p['model'].rsplit('/',1)
                if len(name) > 1:
                    self.propNames.append(name[1])
                    self.props[name[1]] = prop
                else:
                    self.propNames.append(p['model'])
                    self.props[p['model']] = prop

        #controls
        propsMenu = DirectOptionMenu(pos=(0.9,0,0.75),scale=0.1,items=self.propNames,command=self.loadProp)
        propsMenu.setItems()

        self.taskMgr.add(self.manipulationTask,'manipulationTask')
        self.accept("mouse1", self.mouseDispatcher)
        self.accept("mouse1-up", self.releaseProp)

        self.accept("shift-mouse1", self.mouseDispatcherMod)
        self.accept("shift-up", self.releasePropY)

        self.accept("control-e",self.export)

        self.accept("delete",self.setKey,["delete",True])
        self.accept("delete-up",self.setKey,["delete",False])

        
        self.taskMgr.add(self.cameraControlTask,'cameraControlTask')
        self.accept('w', self.setKey, ["forward",True])
        self.accept('w-up', self.setKey, ["forward",False])
        self.accept('a', self.setKey, ["left",True])
        self.accept('a-up', self.setKey, ["left",False])
        self.accept('s', self.setKey, ["backwards",True])
        self.accept('s-up', self.setKey, ["backwards",False])
        self.accept('d', self.setKey, ["right",True])
        self.accept('d-up', self.setKey, ["right",False])
        self.accept('i', self.setKey, ["rot-up",True])
        self.accept('i-up', self.setKey, ["rot-up",False])
        self.accept('j', self.setKey, ["rot-left",True])
        self.accept('j-up', self.setKey, ["rot-left",False])
        self.accept('k', self.setKey, ["rot-down",True])
        self.accept('k-up', self.setKey, ["rot-down",False])
        self.accept('l', self.setKey, ["rot-right",True])
        self.accept('l-up', self.setKey, ["rot-right",False])

        self.accept('m',self.changeMode)

        #Commands
        commandsText = ('Commands:\n\nMove camera: w,a,s,d\nRotate camera: i,j,k,l\nInsert object: select from the dropdown menu\nDelete last selected object: del\nChange mode(Move/Rotate): m\nMove/Rotate object horizontally: left mouse button\nMove/Rotate object vertically: shift + left mouse button\nExport: Ctrl + e')
        self.commandsOSText = OnscreenText(text=commandsText,pos=(-1.7,0.85),align=TextNode.ALeft,mayChange=1)

        self.taskMgr.add(self.tmpTextUpdate,'tmpTextUpdate')

        #Tmp text
        self.tmpText = OnscreenText(text="",pos=(1.0,0.85),align=TextNode.ACenter,mayChange=1,fg=(1,0,0,1))

        


    def export(self):
        camera = True
        first = False
        scene_cfg = {"base": "", "props": []}
        for child in render.getChildren():
            if camera:
                camera = False
                first = True
            elif first:#it is the room/terrain
                scene_cfg["base"] = child.name
                first = False
            else:
                pos = child.getPos()
                rot = child.getHpr()
                prop = {"model": child.name,"position": [pos[0],pos[1],pos[2]], "rotation": [rot[0],rot[1],rot[2]]}
                scene_cfg["props"].append(prop)
        dump = open('export/scene.json',"w")
        dump.write(json.dumps(scene_cfg))
        dump.close()
        self.tmpText.setText("Exported as export/scene.json")
        self.tmpTextTimer = Timer('tmpText') 
        self.tmpTextTimer.start(2,'tmpText')


    def loadProp(self,prop):
        nodeCopy = copy.deepcopy(self.props[prop])
        nodeCopy.reparentTo(render)

    def mouseDispatcher(self):
        if self.mode == MOVE_MODE:
            self.grabProp()
        elif self.mode == ROTATE_MODE:
            self.rotateProp()

    def mouseDispatcherMod(self):
        if self.mode == MOVE_MODE:
            self.grabPropY()
        elif self.mode == ROTATE_MODE:
            self.rotatePropY()


    def grabProp(self):
        if self.cQueue.getNumEntries() > 0:
            self.dragging = True

    def releaseProp(self):
        self.dragging = False
        self.rotating = False

    def grabPropY(self):
        if self.cQueue.getNumEntries() > 0:
            self.dragging = True
            self.dragMod = True

    def releasePropY(self):
        self.dragging = False
        self.dragMod = False
        self.rotating = False


    def rotateProp(self):
        self.mousePosForRot = Vec2(self.mouseWatcherNode.getMouse().getX(),0)
        self.rotating = True

    def rotatePropY(self):
        self.mousePosForRot = Vec2(0,self.mouseWatcherNode.getMouse().getY())
        self.rotating = True



    def pointAtZ(self,z,point,vec):
        if vec.getZ() != 0:
            return point + vec * ((z-point.getZ()) / vec.getZ())
        return LPoint3f(0,0,0)

    def pointAtY(self,y,point,vec):
        if vec.getY() != 0:
            return point + vec * ((y - point.getY()) / vec.getY())
        return LPoint3f(0,0,0)


    def manipulationTask(self,task):
        if self.selected != None: 
            if self.dragging:
                mpos = self.mouseWatcherNode.getMouse()
                self.pickerRay.setFromLens(self.camNode,mpos.getX(),mpos.getY())
                nearPoint = render.getRelativePoint(camera,self.pickerRay.getOrigin())
                nearVec = render.getRelativeVector(camera, self.pickerRay.getDirection())
                if self.dragMod:
                    self.selected.getIntoNodePath().getParent().setPos(self.pointAtY(.5,nearPoint,nearVec))
                else:
                    self.selected.getIntoNodePath().getParent().setPos(self.pointAtZ(.5,nearPoint,nearVec))
            elif self.rotating:
                mpos = Vec2(self.mouseWatcherNode.getMouse().getX(),self.mouseWatcherNode.getMouse().getY())
                curr_h = self.selected.getIntoNodePath().getParent().getParent().getH()
                curr_p = self.selected.getIntoNodePath().getParent().getParent().getP()
                curr_r = self.selected.getIntoNodePath().getParent().getParent().getR()
                new_pos = Vec2(0,0)
                if self.mousePosForRot[0] != 0:
                    new_pos[0] = mpos[0] - self.mousePosForRot[0]
                else:
                    new_pos[1] = mpos[1] - self.mousePosForRot[1]
                self.selected.getIntoNodePath().getParent().getParent().setHpr(curr_h + new_pos[0] * 10,curr_p + new_pos[1] * 10, curr_r)
            else:
                self.selected.getIntoNodePath().hide()
                self.lastSelected = self.selected
                self.selected = None
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            self.pickerRay.setFromLens(self.camNode,mpos.getX(),mpos.getY())
            if self.cQueue.getNumEntries():
                node = self.cQueue.getEntry(0)
                node.getIntoNodePath().show()
                self.selected = node

        if self.keyMapping['delete'] and self.lastSelected != None:
            to_del = self.lastSelected.getIntoNodePath().getParent().getParent()
            to_del.removeNode()

        return task.cont

    def setKey(self,key,val):
        self.keyMapping[key] = val

    def cameraControlTask(self,task):
        dt = globalClock.getDt()

        if self.keyMapping['forward']:
            self.camera.setY(self.camera, +10 * dt)
        if self.keyMapping['backwards']:
            self.camera.setY(self.camera, -10 * dt)
        if self.keyMapping['left']:
            self.camera.setX(self.camera, -10 * dt)
        if self.keyMapping['right']:
            self.camera.setX(self.camera, +10 * dt)
        if self.keyMapping['rot-up']:
            self.camera.setP(self.camera.getP() + 100 * dt)
        if self.keyMapping['rot-down']:
            self.camera.setP(self.camera.getP() - 100 * dt)
        if self.keyMapping['rot-left']:
            self.camera.setH(self.camera.getH() + 100 * dt)
        if self.keyMapping['rot-right']:
            self.camera.setH(self.camera.getH() - 100 * dt)




        return task.cont

    def tmpTextUpdate(self,task):
        dt = globalClock.getDt()
        if self.tmpTextTimer:
            if self.tmpTextTimer.getT() <= 0.0:
                self.tmpTextTimer.stop()
                self.tmpText.setText("")
        return task.cont

    def changeMode(self):
        if self.mode == MOVE_MODE:
            self.mode = ROTATE_MODE
        else:
            self.mode = MOVE_MODE

sb = SceneBuilder()
sb.run()
