/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
** Copyright (c) 2010, Monash University
** All rights reserved.
** Redistribution and use in source and binary forms, with or without modification,
** are permitted provided that the following conditions are met:
**
**       * Redistributions of source code must retain the above copyright notice,
**          this list of conditions and the following disclaimer.
**       * Redistributions in binary form must reproduce the above copyright
**         notice, this list of conditions and the following disclaimer in the
**         documentation and/or other materials provided with the distribution.
**       * Neither the name of the Monash University nor the names of its contributors
**         may be used to endorse or promote products derived from this software
**         without specific prior written permission.
**
** THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
** "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
** THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
** PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
** BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
** CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
** SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
** HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
** LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
** OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
**
**
** Contact:
*%  Owen Kaluza - Owen.Kaluza(at)monash.edu
*%
*% Development Team :
*%  http://www.underworldproject.org/aboutus.html
**
**~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
//Model - handles model data files
#ifndef Model__
#define Model__

#include "sqlite3/sqlite3.h"

#include "Session.h"
#include "Util.h"
#include "GraphicsUtil.h"
#include "ColourMap.h"
#include "View.h"
#include "Geometry.h"
#include "TimeStep.h"

#define SQL_QUERY_MAX 4096

class Database
{
  friend class Model; //Allow private access from Model
private:
  bool readonly;
  bool silent;
  char SQL[SQL_QUERY_MAX];

protected:
  TimeStep* attached;
  char prefix[10];    //attached db prefix
  sqlite3 *db;
  FilePath file;
  bool memory;

public:

  Database();
  Database(const FilePath& fn);
  ~Database();

  bool open(bool write=false);
  void reopen(bool write=false);
  void attach(TimeStep* timestep);

  sqlite3_stmt* select(const char* fmt, ...);
  bool issue(const char* fmt, ...);

  operator bool() const { return db != NULL; }
};

class Model
{
private:
  int now;            //Loaded step per model

public:
  Session& session;
  Database database;

  std::vector<std::string> fignames;
  std::vector<std::string> figures;
  int figure;

  std::vector<TimeStep*> timesteps;
  std::vector<View*> views;
  std::vector<DrawingObject*> objects;
  std::vector<ColourMap*> colourMaps;

  std::vector<Geometry*> fixed;     //Static geometry
  //Current timestep geometry
  std::vector<Geometry*> geometry;
  //Previous timestep geometry
  std::vector<Geometry*> olddata;

  DrawingObject* borderobj;
  DrawingObject* axisobj;
  DrawingObject* rulerobj;

  float min[3], max[3]; //Calculated model bounding box

  Geometry* getRenderer(lucGeometryType type, std::vector<Geometry*>& renderers);
  Geometry* getRenderer(lucGeometryType type);
  Geometry* getRenderer(const std::string& what);
  Geometry* createRenderer(const std::string& what);

  void clearObjects();
  void setup();
  void reload(DrawingObject* obj);
  void redraw(bool reload=false);
  void loadWindows();
  void loadLinks();
  void loadLinks(DrawingObject* obj);
  void clearTimeSteps();
  int loadTimeSteps(bool scan=false);
  void loadFixed();
  bool inFixed(DataContainer* block0);
  std::string checkFileStep(unsigned int ts, const std::string& basename, unsigned int limit=1);
  void loadViewports();
  void loadViewCamera(int viewport_id);
  void loadObjects();
  void loadColourMaps();
  void loadColourMapsLegacy();
  void setColourMapProps(Properties& properties, float  minimum, float maximum, bool logscale, bool discrete);

  Model(Session& session);
  void load(const FilePath& fn);
  void init();
  ~Model();

  bool loadFigure(int fig);
  void storeFigure();
  int addFigure(std::string name="", const std::string& state="");
  void addObject(DrawingObject* obj);
  ColourMap* addColourMap(std::string name="", std::string colours="", std::string properties="");
  void updateColourMap(ColourMap* colourMap, std::string colours="", std::string properties="");
  DrawingObject* findObject(unsigned int id);
  View* defaultView();

  //Data fix
  void freeze();

  //Timestep caching
  void cacheLoad();
private:
  bool useCache();
  void cacheStep();
  bool restoreStep();
  void clearStep();
  void printCache();

public:
  int step()
  {
    //Current actual step
    return now < 0 || (int)timesteps.size() <= now ? -1 : timesteps[now]->step;
  }

  int stepInfo()
  {
    //Current actual step (returns 0 if none instead of -1 for output functions)
    return now < 0 || (int)timesteps.size() <= now ? 0 : timesteps[now]->step;
  }

  int lastStep()
  {
    if (timesteps.size() == 0) return -1;
    return timesteps[timesteps.size()-1]->step;
  }

  bool hasTimeStep(int ts);
  int nearestTimeStep(int requested);
  void addTimeStep(int step=0, double time=-HUGE_VAL, const std::string& path="")
  {
    if (time == -HUGE_VAL) time = step;
    timesteps.push_back(new TimeStep(step, time, path));
  }

  int setTimeStep(int stepidx, bool skipload=false);
  int loadGeometry(int obj_id=0, int time_start=-1, int time_stop=-1);
  int loadFixedGeometry();
  int readGeometryRecords(sqlite3_stmt* statement, bool cache=true);
  void mergeDatabases();
  void updateObject(DrawingObject* target, lucGeometryType type, bool compress=true);
  void writeDatabase(const char* path, DrawingObject* obj, bool compress=false);
  void writeState();
  void writeState(Database& outdb);
  void writeObjects(Database& outdb, DrawingObject* obj, int step, bool compress);
  void deleteGeometry(Database& outdb, lucGeometryType type, DrawingObject* obj, int step);
  void writeGeometry(Database& outdb, Geometry* g, DrawingObject* obj, int step, bool compress);
  void writeGeometryRecord(Database& outdb, lucGeometryType type, lucGeometryDataType dtype, unsigned int objid, Geom_Ptr data, DataContainer* block, int step, bool compressdata);
  void deleteObject(unsigned int id);
  void backup(Database& fromdb, Database& todb);
  void calculateBounds(View* aview, float* default_min=NULL, float* default_max=NULL);
  void objectBounds(DrawingObject* draw, float* min, float* max);

  std::string jsonWrite(bool objdata=false);
  void jsonWrite(std::ostream& os, DrawingObject* obj=NULL, bool objdata=false);
  void jsonRead(std::string data);
};

#endif //Model__
