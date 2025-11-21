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

  (20.11.2025) Error with javascript syntax, dosent allow me to press anybuttons. AT TIME Claude code version - 27v  
  (11:23PM)Clean and fixed version works a lot better, now allows to edit CSV or JSON file format, and save those values. Cannot access, bounding box, gives faulty *Get BOM* results using ID's.  
  (02.51PM) OnShape API with data base - began working on data base for OnShapes API, to save *keys* and *ID's* for every user that is using it, and as *primary key* using *emails* or custom *username* , made by a person itself, later for the coresponding *email* or *user* that *keys* and *ID's* will be used for OAuth and to authorize account for usage with *This api -> OnShapes Rest API* for comunnication or fetching files.  

  (21.11.2025) DataBase finished, now server can also pull data depending on the login user. Save ID's such as WorkSpace, Elemenet and Document. Push File back to OnShape - Currently unsusessful, can Log out, can choose what format BOM is - working 50/50, EVERYTHING else stays pretty much the same.  
  (02.45 PM) Recived new info about what to do, for server, where to add BOM overrwrite values. Created a new Issue in github - "Vai ir iespējams dabūt no configurācijām "Variable" kas ir iedvadīts deteļai kā garums, to kautkā ievilkt garuma property"".  






               This page is created for a issue with OnShape seen in company named - Mechanika Engineering.  
               Created by an Intern at company - Aleks Ņikitins, Internship time by Valmieras Tehnikums from 27.10.2025 till 15.12.2025.  
               GitHub repository is owned by the creator - Aleks Ņikitins.
