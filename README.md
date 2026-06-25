# Ground-Track Dashboard

Full-stack satellite flight dynamics dashboard that live tracks real objects in orbit using live data from CelesTrak.org [mirror: PocketWorld.org].  
Includes orbital elements, geodetic coordinates, customizable selection of flying objects, passes above 10deg of elevation

Releases:  
Linux: v1.2.0  
Windows: v1.2.0.exe  
To debug, run:  
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; installer.bat,  
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; run.bat  
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; [satellite-dashboard/main_mirror.py]  
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; [satellite-dashboard/orbital.py]  
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; [static/index.html]  

Local hosts: [http://127.0.0.1:8000/docs#](http://127.0.0.1:8000/docs#)  dashboard  
&emsp;&emsp;&emsp;&emsp;&emsp; [http://127.0.0.1:8000](http://127.0.0.1:8000)  map

Latest release hosted on render: [https://ground-track-dashboard.onrender.com](https://ground-track-dashboard.onrender.com)

Known bug: the TLE don't get automatically upgraded in the render hosted version

Added: Visibility mask around Ground Station (Elevation > 10deg), increased polling to 1Hz