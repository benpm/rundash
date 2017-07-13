# Rundash
A simple online racing-platformer made to run on most browsers / systems! [Here is a demo](https://codepen.io/_bm/full/QgVPqo/).

# Design
Here is the [design document](https://docs.google.com/document/d/1luPd_t-Zen7it4TMPxJb4RIFfKE-jRKTVQ8oJJ5pEbw/edit?usp=sharing) we are currently working with.

# Implementation
The game client is written in JavaScript using JQuery, Polyfill and Sprintf. It requires neither the canvas element nor WebGL to run. All graphics are driven by plain CSS, HTML and SVG graphics.
The server is written in python using Flask-SocketIO.
