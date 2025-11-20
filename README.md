# OnShape_Server_API (Temporarily)
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
  
  The rendering time depends greatly on the amount of data or imports or other information being read, the time can reach up to 1+ minutes, currently the approximate observed time is about _1 min to around 5 min, depending on what is new, and what has to be overrided (13.11.2025)_   
    
  (13.11.2025) Website is able to start correctly, make contact with the OnShape API to request authorization but cannot save token "_Token Exchange Failed
Status Code: 400_". Also it is able to check API working statuss. 

  (19.11.2025) Website is able to start corretly, make conctact with OnShape API, to request OAuth for authorization, Is able to save tokens that can be used for *1* Hours, is able to give access key, is able to fetch documents, is able to save, pull, and scan for ID's, Is able to save values in *JSON* or *CSV* file format, is able to get *BOM, Bounding Box, List of my documents, and get document elements*

  (20.11.2025) Error with javascript syntax, dosent allow me to press anybuttons.
