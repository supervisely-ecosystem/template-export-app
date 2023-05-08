import json, os
import supervisely as sly

from dotenv import load_dotenv
from tqdm import tqdm

# load ENV variables for debug, has no effect in production
load_dotenv("local.env")
load_dotenv(os.path.expanduser("~/supervisely.env"))


STORAGE_DIR = sly.app.get_data_dir() # path to directory for temp files and result archive
ANN_FILE_NAME = "labels.json"


class MyExport(sly.app.Export):
    def process(self, context: sly.app.Export.Context):
        # create api object to communicate with Supervisely Server
        api = sly.Api.from_env()

        # get project info from server
        project_info = api.project.get_info_by_id(id=context.project_id)

        # make project directory path
        data_dir = os.path.join(STORAGE_DIR, f"{project_info.id}_{project_info.name}")

        # get project meta
        meta_json = api.project.get_meta(id=context.project_id)
        project_meta = sly.ProjectMeta.from_json(meta_json)

        # Check if the app runs from the context menu of the dataset. 
        if context.dataset_id is not None:
            # If so, get the dataset info from the server.
            dataset_infos = [api.dataset.get_info_by_id(context.dataset_id)]
        else:
            # If it does not, obtain all datasets infos from the current project.
            dataset_infos = api.dataset.get_list(context.project_id)

        # iterate over datasets in project
        for dataset in dataset_infos:
            result_anns = {}

            # get dataset images info
            images_infos = api.image.get_list(dataset.id)

            # track progress using Tqdm
            with tqdm(total=dataset.items_count) as pbar:
                # iterate over images in dataset
                for image_info in images_infos:
                    labels = []

                    # create path for each image and download it from server
                    image_path = os.path.join(data_dir, dataset.name, image_info.name)
                    api.image.download(image_info.id, image_path)

                    # download annotation for current image
                    ann_json = api.annotation.download_json(image_info.id)
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

                    result_anns[image_info.name] = labels

                    # increment the current progress counter by 1
                    pbar.update(1)

            # create JSON annotation in new format
            filename = os.path.join(data_dir, dataset.name, ANN_FILE_NAME)
            with open(filename, "w") as file:
                json.dump(result_anns, file, indent=2)

        return data_dir


app = MyExport()
app.run()
