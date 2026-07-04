State Chart Diagram Editor with Labeled Transition Links
This sample creates a state chart to story-board an online shopping experience.

The text is editable for both the Nodes and the Links. The user can draw as many links from one Node to another Node as desired. To create a new Link start dragging from the edge of a Node. The Links can be reshaped or deleted when selected. Double-clicking in the background of the Diagram creates a new node. The mouse wheel is set to zoom in and out instead of scroll.

This sample customizes the Part.selectionAdornmentTemplate of the node to a template that contains a button. The button is positioned to be at the Top-Right corner of the node by being in a Spot Panel with its GraphObject.alignment property set to Spot.TopRight.

The Button's GraphObject.click method creates a new node data, adds it to the model, and creates a link from the original node data to the new node data. All of this is done inside a transaction, so that it can be undone by the user (Ctrl+Z and Ctrl+Y will undo and redo transactions). After the node is created, CommandHandler.scrollToPart is called to try to center it.



However the npm package contains only the library. You can install the GoJS library using npm:

$ npm install gojs
The samples, extensions, and documentation can be installed by running:

$ npm create gojs-kit


for state diagrams, minimal and best example to use :

{ "class": "go.GraphLinksModel",
  "nodeKeyProperty": "id",
  "pointsDigits": 0,
  "nodeDataArray": [
  {"id":-1, "loc":"171 -165", "type":"Start", "text":"Start" },
  {"id":0, "loc":"209 17", "text":"Shopping"},
  {"id":1, "loc":"388 35", "text":"Browse Items"},
  {"id":2, "loc":"388 183", "text":"Search Items"},
  {"id":3, "loc":"607 13", "text":"View Item"},
  {"id":4, "loc":"770 -105", "text":"View Cart"},
  {"id":5, "loc":"726 110", "text":"Update Cart"},
  {"id":6, "loc":"935 22", "text":"Checkout"},
  {"id":-2, "loc":"913 220", "type":"End", "text":"End" }
  ],
  "linkDataArray": [
    { "from": -1, "to": 0, "progress": true, "text": "Visit online store", "curviness": -10 },
    { "from": 0, "to": 1,  "progress": true, "text": "Browse" },
    { "from": 0, "to": 2,  "progress": true, "text": "Use search bar", "curviness": -70 },
    { "from": 1, "to": 2,  "progress": true, "text": "Use search bar" },
    { "from": 2, "to": 3,  "progress": true, "text": "Click item", "curviness": -70 },
    { "from": 2, "to": 2,  "progress": false, "text": "Another search", "curviness": 40 },
    { "from": 1, "to": 3,  "progress": true, "text": "Click item" },
    { "from": 3, "to": 0,  "progress": false, "text": "Not interested", "curviness": -100 },
    { "from": 3, "to": 4,  "progress": true, "text": "Add to cart" },
    { "from": 4, "to": 0,  "progress": false, "text": "More shopping", "curviness": -150 },
    { "from": 4, "to": 5,  "progress": false, "text": "Update needed", "curviness": 70 },
    { "from": 5, "to": 4,  "progress": false, "text": "Update made" },
    { "from": 4, "to": 6,  "progress": true, "text": "Proceed" },
    { "from": 6, "to": 5,  "progress": false, "text": "Update needed"},
    { "from": 6, "to": -2, "progress": true, "text": "Purchase made" }
  ]
}
    
