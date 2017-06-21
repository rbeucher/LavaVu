//IPython kernel object
var kernel;
if (parent.IPython) {
  kernel = parent.IPython.notebook.kernel;
}

//Maintain a list of interactor instances opened by id
//(check in case this script imported twice, don't overwrite previous)
var _wi = window._wi ? window._wi : [];
var delay = 0;
function debug_kernel(cmd) {
  //For debugging:
  //Run a python command in kernel and log output to console
  if (kernel) {
    kernel.execute(cmd);
    //Debug callback
    var callbacks = {'output' : function(out) {
        data = out.content.data['text/plain']
        console.log("CMD: " + cmd + ", RESULT: " + data);
      }
    };
    kernel.execute(cmd, {iopub: callbacks}, {silent: false});
  }
}

function getUrl() {
  var loc = window.location;
  var baseUrl = loc.protocol + "//" + loc.hostname + (loc.port ? ":" + loc.port : "");
  return baseUrl;
}

function WindowInteractor(id) {
  //Store self in list and save id
  this.id = id;
  
  console.log("New interactor: " + this.id);
  //Interactor class, handles javascript side of window control
  //Takes viewer id
  // - set as active target for commands
  // - init webgl bounding box
  // - display initial image
  this.img = document.getElementById("imgtarget_" + this.id);

  //No window
  if (!this.img) return;

  //Initial image
  //(Init WebGL bounding box interaction on load)
  var that = this;
  this.get_image(function() {
    //console.log('In image loaded callback ' + that.id);
    //Init on image load with callback function to execute commands
    that.box = initBox(that.img, function(cmd) {that.execute(cmd, true);});
    //console.log("Box init on " + that.id);
    //Update the box size by getting state
    updateBox(that.box, function(onget) {that.get_state(onget);});
    //Clear onload
    that.img.onload = null;
  });
}

WindowInteractor.prototype.execute = function(cmd, instant) { //, viewer_id) {
  //console.log("execute: " + cmd);
  if (kernel) {
    kernel.execute('lavavu.control.windows[' + this.id + '].commands("' + cmd + '")');
    this.get_image();
  } else {
    //HTTP interface
    //Replace newlines with semi-colon first
    cmd = cmd.replace(/\n/g,';');
    if (instant && this.img) {
      var url = getUrl() + "/icommand=" + cmd + "?" + new Date().getTime();
      this.img.onload = null;
      this.img.src = url;
    } else {
      var url = getUrl() + "/command=" + cmd + "?" + new Date().getTime()
      x = new XMLHttpRequest();
      x.open('GET', url, true);
      x.send();
      this.get_image();
    }

  }
  return false;
}

WindowInteractor.prototype.set_prop = function(obj, prop, val) {
  this.execute("select " + obj + "; " + prop + "=" + val);
  this.get_image();
}

WindowInteractor.prototype.do_action = function(id, val) {
  if (kernel) {
    //Non-numeric, add quotes and strip newlines
    if (typeof(val) == 'string' && ("" + parseFloat(val) !== val)) {
      val = val.replace(/\n/g,';');
      val = '"' + val + '"';
    }
    kernel.execute('cmds = lavavu.control.action(' + id + ',' + val + ')');
    kernel.execute('if len(cmds): lavavu.control.windows[' + this.id + '].commands(cmds)');
    this.get_image();
  } else {
    //HTML control actions via http
    actions[id](val);
  }

  //Reload state
  if (this.img) {
    var that = this;
    updateBox(this.box, function(onget) {that.get_state(onget);});
  }
}

WindowInteractor.prototype.redisplay = function() {
  //console.log("redisplay: " + this.id);
  if (this.img) {
    //Call get_image
    this.get_image();
    //Update the box size by getting state
    var that = this;
    updateBox(that.box, function(onget) {that.get_state(onget);});
  }
}

WindowInteractor.prototype.get_image = function(onload) {
  if (!this.img) return;
  //console.log("get_img: " + this.id);
  if (kernel) {
    var that = this;
    var callbacks = {'output' : function(out) {
        //Skip first message we get without data
        //if (!out.content.data) {console.log(JSON.stringify(out)); return;}
        if (!out.content.data) return;
        data = out.content.data['text/plain']
        data = data.substring(1, data.length-1)
        //console.log("Got image: " + data.length);
        if (that.img) {
          //Only set onload if provided
          if (onload) // && !that.img.onload)
            that.img.onload = onload;
          that.img.src = data;
        }
      }
    };

    kernel.execute('lavavu.control.windows[' + this.id + '].frame()', {iopub: callbacks}, {silent: false});
  } else {
    //if (!this.img) this.img = document.getElementById('imgtarget_0');
    var url = getUrl() + "/image?" + new Date().getTime();
    if (this.img) {
      this.img.onload = onload;
      this.img.src = url;
    }
  }
}

WindowInteractor.prototype.get_state = function(onget) {
  //console.log("get_state: " + this.id);
  if (kernel) {
    var callbacks = {'output' : function(out) {
        //if (!out.content.data) {console.log(JSON.stringify(out)); return;}
        if (!out.content.data) return;
        data = out.content.data['text/plain']
        data = data.replace(/(?:\\n)+/g, "");
        data = data.substring(1, data.length-1)
        onget(data);
      }
    };
    kernel.execute('lavavu.control.windows[' + this.id + '].app.getState()', {iopub: callbacks}, {silent: false});
  }
  else {
    var url = getUrl() + "/getstate"
    x = new XMLHttpRequest();
    x.onload = function() { 
      if(x.status == 200)
        onget(x.response);
      else  
        console.log("Ajax Request Error: " + url + ", returned status code " + x.status + " " + x.statusText);
    } 
    x.open('GET', url, true);
    x.send();
  }
}


