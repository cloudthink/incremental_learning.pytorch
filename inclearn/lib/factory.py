import warnings

import torch
from torch import optim

from inclearn import models
from inclearn.convnet import (densenet, my_resnet, my_resnet2, my_resnet_brn,
                              resnet, ucir_resnet)
from inclearn.lib import data, schedulers


def get_optimizer(params, optimizer, lr, weight_decay=0.0):
    if optimizer == "adam":
        return optim.Adam(params, lr=lr, weight_decay=weight_decay)
    elif optimizer == "adamw":
        return optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    elif optimizer == "sgd":
        return optim.SGD(params, lr=lr, weight_decay=weight_decay, momentum=0.9)

    raise NotImplementedError


def get_convnet(convnet_type, **kwargs):
    if convnet_type == "resnet18":
        return resnet.resnet18(**kwargs)
    elif convnet_type == "resnet34":
        return resnet.resnet34(**kwargs)
    elif convnet_type == "resnet32":
        return resnet.resnet32(**kwargs)
    elif convnet_type == "rebuffi":
        return my_resnet.resnet_rebuffi(**kwargs)
    elif convnet_type == "rebuffi_brn":
        return my_resnet_brn.resnet_rebuffi(**kwargs)
    elif convnet_type == "myresnet18":
        return my_resnet2.resnet18(**kwargs)
    elif convnet_type == "myresnet34":
        return my_resnet2.resnet34(**kwargs)
    elif convnet_type == "densenet121":
        return densenet.densenet121(**kwargs)
    elif convnet_type == "ucir":
        return ucir_resnet.resnet32(**kwargs)

    raise NotImplementedError("Unknwon convnet type {}.".format(convnet_type))


def get_model(args):
    if args["model"] == "icarl":
        return models.ICarl(args)
    elif args["model"] == "lwf":
        return models.LwF(args)
    elif args["model"] == "e2e":
        return models.End2End(args)
    elif args["model"] == "medic":
        return models.Medic(args)
    elif args["model"] == "focusforget":
        return models.FocusForget(args)
    elif args["model"] == "fixed":
        return models.FixedRepresentation(args)
    elif args["model"] == "bic":
        return models.BiC(args)
    elif args["model"] == "icarlmixup":
        return models.ICarlMixUp(args)
    elif args["model"] == "ucir":
        return models.UCIR(args)
    elif args["model"] == "test":
        return models.Test(args)
    elif args["model"] == "still":
        return models.STILL(args)

    raise NotImplementedError("Unknown model {}.".format(args["model"]))


def get_data(args, class_order=None):
    return data.IncrementalDataset(
        dataset_name=args["dataset"],
        random_order=args["random_classes"],
        shuffle=True,
        batch_size=args["batch_size"],
        workers=args["workers"],
        validation_split=args["validation"],
        onehot=args["onehot"],
        increment=args["increment"],
        initial_increment=args["initial_increment"],
        sampler=get_sampler(args),
        sampler_config=args.get("sampler_config", {}),
        data_path=args["data_path"],
        class_order=class_order,
        seed=args["seed"],
        dataset_transforms=args.get("dataset_transforms", {})
    )


def set_device(args):
    devices = []

    for device_type in args["device"]:
        if device_type == -1:
            device = torch.device("cpu")
        else:
            device = torch.device("cuda:{}".format(device_type))

        devices.append(device)

    args["device"] = devices


def get_sampler(args):
    if args["sampler"] is None:
        return None

    sampler_type = args["sampler"].lower().strip()

    if sampler_type == "npair":
        return data.NPairSampler
    elif sampler_type == "triplet":
        return data.TripletSampler
    elif sampler_type == "tripletsemihard":
        return data.TripletCKSampler

    raise ValueError("Unknown sampler {}.".format(sampler_type))


def get_lr_scheduler(
    scheduling_config, optimizer, nb_epochs, lr_decay=0.1, warmup_config=None, task=0
):
    if isinstance(scheduling_config, str):
        warnings.warn("Use a dict not a string for scheduling config!", DeprecationWarning)
        scheduling_config = {"type": scheduling_config}
    elif isinstance(scheduling_config, list):
        warnings.warn("Use a dict not a list for scheduling config!", DeprecationWarning)
        scheduling_config = {"type": "step", "epochs": scheduling_config}

    if scheduling_config["type"] == "step":
        scheduler = torch.optim.lr_scheduler.MultiStepLR(
            optimizer, scheduling_config["epochs"], gamma=lr_decay
        )
    elif scheduling_config["type"] == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, nb_epochs)
    elif scheduling_config["type"] == "cosine_with_restart":
        scheduler = schedulers.CosineWithRestarts(
            optimizer,
            t_max=scheduling_config.get("cycle_len", nb_epochs),
            factor=scheduling_config.get("factor", 1.)
        )
    else:
        raise ValueError("Unknown LR scheduling type {}.".format(scheduling_config["type"]))

    if warmup_config:
        if warmup_config.get("only_first_step", True) and task != 0:
            pass
        else:
            print("Using WarmUp")
            scheduler = schedulers.GradualWarmupScheduler(
                optimizer=optimizer, after_scheduler=scheduler, **warmup_config
            )

    return scheduler
