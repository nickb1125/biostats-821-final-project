"""Create and train PyTorch NBA model"""
import torch
import torch.nn as nn
import torch.nn.functional as F

# Create and train the NBA model

class NBA_Model(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        

