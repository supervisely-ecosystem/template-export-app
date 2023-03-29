# Create export app from template

## Introduction

In this tutorial, you will learn how to create custom export app for exporting your data from Supervisely platform using an [export template app](https://github.com/supervisely-ecosystem/template-export-app) that we have prepared for you.

We advise reading our [from script to supervisely app](https://developer.supervise.ly/app-development/basics/from-script-to-supervisely-app) guide if you are unfamiliar with the [file structure](https://developer.supervise.ly/app-development/basics/from-script-to-supervisely-app#repository-structure) of a Supervisely app repository because it addresses the majority of the potential questions.

We will go through the following steps:

[**Step 1.**](#step-1-set-up-an-environment-for-development) Set up an environment for development.

[**Step 2.**](#step-2-how-to-debug-export-app) How to debug export app.

[**Step 3.**](#step-3-what-custom-export-app-do) What custom export app do.

[**Step 4**](#step-4-how-to-write-an-export-script) How to write an export script.

[**Step 5.**](#step-5-how-to-run-it-in-supervisely) How to run it in Supervisely.

Everything you need to reproduce [this tutorial is on GitHub](https://github.com/supervisely-ecosystem/template-export-app): source code and additional app files.

## Step 1. Set up an environment for development

**Step 1.** Prepare `~/supervisely.env` file with credentials. [Learn more here.](https://developer.supervise.ly/getting-started/basics-of-authentication#how-to-use-in-python)

**Step 2.** Fork and clone [repository](https://github.com/supervisely-ecosystem/template-export-app) with source code and create [Virtual Environment](https://docs.python.org/3/library/venv.html).

```bash
git clone https://github.com/supervisely-ecosystem/template-export-app
cd export-custom-format
./create_venv.sh
```

**Step 3.** Open repository directory in Visual Studio Code.

```bash
code -r .
```

**Step 4.** Select created virtual environment as python interpreter.

**Step 5.** Open `local.env` and insert your values here. Learn more about environment variables in our [guide](https://developer.supervise.ly/getting-started/environment-variables)

```python
TASK_ID=10                    # ⬅️ requires to use advanced debugging
TEAM_ID=1                     # ⬅️ change it
WORKSPACE_ID=1                # ⬅️ change it
PROJECT_ID=555                # ⬅️ ID of the project that you want to export
DATASET_ID=55555              # ⬅️ ID of the dataset that you want to export (leave empty if you want to export whole project)
```

When running the app from Supervisely platform: Project and Dataset IDs will be automatically detected depending on how you run your application.

## Step 2. How to debug export app

Export template has 2 launch options for debugging:

- `Debug`
- `Advanced debug`

**Option 1. Debug**

This option is good starting point. In this case result archive or folder with exporting data will stay on your computer.

**Option 2. Advanced debug**

The advanced debugging option is somewhat identical, however it will upload result archive or folder with data to `Team Files` instead. This option is an example of how production apps work in Supervisely platform.

## Step 3. What custom export app do

Custom export app converts selected images project or dataset to the following format and prepares downloadable .tar archive:

- original images
- annotations in json format

Output example:

```text
<id_project_name>.tar
- ds0
  - image_1.jpg
  - image_2.jpg
  - labels.json
- ds1
  - image_1.jpg
  - image_2.jpg
  - labels.json
```

Labels.json:

Contain bounding box coordinates(top, left, right, bottom) of all objects in project or dataset

```text
{
"image_1.jpg": [
          {
               "class_name": "cat",
               "coordinates": [top, left, right, bottom]
           },
            {
               "class_name": "cat",
               "coordinates": [top, left, right, bottom]
           },
           {
               "class_name": "dog",
               "coordinates": [top, left, right, bottom]
           },
     ]
}

```

## Step 4. How to write an export script

You can find source code for this example [here](https://github.com/supervisely-ecosystem/template-export-app/blob/master/src/main.py)

**Step 1. Import libraries**

```python
import os, json
import supervisely as sly
from os.path import join

from dotenv import load_dotenv
```

**Step 2. Load environment variables**

Load ENV variables for debug, has no effect in production

```python
load_dotenv("local.env")
load_dotenv(os.path.expanduser("~/supervisely.env"))
```

**Step 3. Write Export script**

Create a class that inherits from `sly.app.Export` and write `process` method that will handle the `team_id`, `workspace_id`, `project_id` and `dataset_id` that you specified in the `local.env`. In this example our class called `MyExport`.

`sly.app.Export` class will handle export routines for you:

- it will check that selected project or dataset exist and that you have access to work with it,
- it will upload your result data to Team Files and clean temporary folder, containing result archive in remote container or local hard drive if you are debugging your app. Your application must return string, containing path to result archive or folder.

`sly.app.Export` has a `Context` subclass which contains all required information that you need for exporting your data from Supervisely platform:

- `Team ID` - shows team id where exporting project or dataset is located
- `Workspace ID` - shows workspace id where exporting project or dataset is located
- `Project ID` - id of exporting project
- `Dataset ID` - id of exporting dataset (detected only if the export is performed from dataset context menu)

`context` variable is passed as an argument to `process` method of class `MyExport` and `context` object will be created automatically when you execute export script.

```python
class MyExport(sly.app.Export):
    def process(self, context: sly.app.Export.Context):
        print(context)
```

Output:

```text
Team ID: 1
Workspace ID: 1
Project ID: 555
Dataset ID: 55555
```

Now let's get to the code part

```python
STORAGE_DIR = sly.app.get_data_dir()
ANN_FILE_NAME = "labels.json"

class MyExport(sly.app.Export):
    def process(self, context: sly.app.Export.Context):
        # create api object to communicate with Supervisely Server
        api = sly.Api.from_env()

        # get project info from server
        project_info = api.project.get_info_by_id(id=context.project_id)

        # make project directory path
        data_dir = join(STORAGE_DIR, f"{project_info.id}_{project_info.name}")

        # get project meta
        meta_json = api.project.get_meta(id=context.project_id)
        project_meta = sly.ProjectMeta.from_json(meta_json)

        # get datasets info from server
        dataset_infos = api.dataset.get_list(project_id=context.project_id)

        # iterate over datasets in project
        for dataset in dataset_infos:
            result_anns = {}

            # create Progress object to track progress
            ds_progress = sly.Progress(
                f"Processing dataset: '{dataset.name}'",
                total_cnt=dataset.images_count,
            )

            # get dataset images info
            images = api.image.get_list(dataset.id)

            # iterate over images in dataset
            for image in images:
                labels = []

                # create path for each image and download it from server
                image_path = join(data_dir, dataset.name, image.name)
                api.image.download(image.id, image_path)

                # download annotation for current image
                ann_json = api.annotation.download_json(image.id)
                ann = sly.Annotation.from_json(ann_json, project_meta)

                # iterate over labels in current annotation
                for label in ann.labels:
                    # get obj class name
                    name = label.obj_class.name

                    # get bounding box coordinates for label
                    bbox = label.geometry.to_bbox()
                    labels.append(
                        {
                            "class_name": name,
                            "coordinates": [
                                bbox.top,
                                bbox.left,
                                bbox.bottom,
                                bbox.right,
                            ],
                        }
                    )

                result_anns[image.name] = labels

                # increment the current progress counter by 1
                ds_progress.iter_done_report()

            # create JSON annotation in new format
            filename = join(data_dir, dataset.name, ANN_FILE_NAME)
            with open(filename, "w") as file:
                json.dump(result_anns, file, indent=2)

        return data_dir
```

Create `MyExport` object and execute `run` method to start export

```python
app = MyExport()
app.run()
```

Output of this python program:

```text
{"message": "Exporting Project: id=555, name=lemons, type=images", "timestamp": "2023-03-09T12:01:44.697Z", "level": "info"}
{"message": "Exporting Dataset: id=55555, name=ds1", "timestamp": "2023-03-09T12:01:45.093Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 0, "total": 6, "timestamp": "2023-03-09T12:01:46.150Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 1, "total": 6, "timestamp": "2023-03-09T12:01:47.360Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 2, "total": 6, "timestamp": "2023-03-09T12:01:48.295Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 3, "total": 6, "timestamp": "2023-03-09T12:01:49.384Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 4, "total": 6, "timestamp": "2023-03-09T12:01:50.233Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 5, "total": 6, "timestamp": "2023-03-09T12:01:51.061Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Processing dataset: 'ds1'", "current": 6, "total": 6, "timestamp": "2023-03-09T12:01:51.891Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Uploading '14957_lemons.tar'", "current": 0, "total": 891297, "current_label": "0.0 B", "total_label": "870.4 KiB", "timestamp": "2023-03-09T12:01:54.116Z", "level": "info"}
{"message": "progress", "event_type": "EventType.PROGRESS", "subtask": "Uploading '14957_lemons.tar'", "current": 891297, "total": 891297, "current_label": "870.4 KiB", "total_label": "870.4 KiB", "timestamp": "2023-03-09T12:01:54.434Z", "level": "info"}
{"message": "Remote file: id=1022869, name=555_lemons.tar", "timestamp": "2023-03-09T12:01:55.410Z", "level": "info"}
```

## Step 5. How to run it in Supervisely

Submitting an app to the Supervisely Ecosystem isn’t as simple as pushing code to github repository, but it’s not as complicated as you may think of it either.

Please follow this [link](https://developer.supervise.ly/app-development/basics/add-private-app) for instructions on adding your app. We have produced a step-by-step guide on how to add your application to the Supervisely Ecosystem.
