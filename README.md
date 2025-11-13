# OnShape_Server_API
Here is saved a website to test if my PYTHON API can comunicate with OnShapes Rest API via website, made with render.com.

**Static folder**  
Holds HTML contorl and navigation panel used for controling, such as pulling or feching files from OnShape and adding them or editing in python.  
**Main.py**  
Holds the main code for the API, editable if needed.  
**Requrments**  
Hold neccecery commands that are used when starting the server by *render.com*  
**Render.com**  
Is used to start the website and allowing to communicate with OnShape via OAuth, API, Diffrent ID's and for fetching files.

Link to access the server - https://onshape-server-api.onrender.com/  
The server can also start as soon as an iteration is performed, it can disconnect if there has been no activity for 15 minutes.

  
  Here will be a link to start the server remotely, if necessary and if the server did not start when the iteration is performed (Open server via link.) Link to open the server remotely   
  https://api.render.com/deploy/srv-d49ikkumcj7s73egu370?key=UL0PHK6ocok
  
  The rendering time depends greatly on the amount of data or imports or other information being read, the time can reach up to 1+ minutes, currently the approximate observed time is about 15-30sec.
