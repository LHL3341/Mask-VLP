import warnings
warnings.filterwarnings("ignore")
import sys
import os
sys.path[0] = os.path.abspath('.')
import json
import random
import torch
from torch import autograd
import tqdm
from torch import nn, optim
import torch.nn.functional as F
from PIL import Image
from pathlib import Path
from collections import defaultdict
import sys
import torchvision.transforms as transforms
from volta_src.config import BertConfig
from models.vit import VisionTransformer, interpolate_pos_embed
from models.med import BertConfig, BertModel, BertLMHeadModel 
from volta_src.embeddings import BertLayerNorm
from volta_src.encoders import GeLU
from extras_ import convert_sents_to_features, BertLayer
import argparse
from urllib.parse import urlparse
from timm.models.hub import download_cached_file
from utils import pre_caption

from transform.randaugment import RandomAugment
from torchvision.transforms.functional import InterpolationMode

from models.contextual_new import Adapter_BLIP
import yaml


testset_path = 'dataset/test_data_unlabeled.json'
output_path = 'res/9.json'
model_path = 'Models/pretrain/no_mim_2d/42/3175.pth'
img_dirs = 'dataset/image-sets'

test_data = json.load(open(testset_path, 'r'))

bert_config = json.load(open('vilbert-and-bert-config.json', 'r'))
model = Adapter_BLIP(reduction=2)
checkpoint = torch.load(model_path)
model.load_state_dict(checkpoint['model'],strict= False)
model.cuda()
model.eval()
res = test_data.copy()
for img_dir, data in tqdm.tqdm(test_data.items()): # dir
    ids = []
    for text in data: # gt, text
        text = [pre_caption(text)]
        img_files = list((Path(img_dirs) / img_dir).glob("*.jpg"))
        img_files = sorted(img_files, key=lambda x: int(str(x).split('/')[-1].split('.')[0][3:]))
        images = [Image.open(photo_file).convert("RGB") for photo_file in img_files]
        preprocess = transforms.Compose([
            transforms.Resize((224,224),interpolation=InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
            ])  
        images = [preprocess(image) for image in images]
        image = torch.stack(images).cuda()
        with torch.no_grad():
            output = model(image, text).squeeze()
            logits = model.pretrained_blip.itm_head(output[:,0,:])
            itm_score = torch.nn.functional.softmax(logits,dim=1)[:,1]
        pred = torch.argmax(itm_score).squeeze()
        ids.append(int(pred))
    res[img_dir] = ids
with open(output_path,'w')as f:
    json.dump(res,f)
print('finish')
