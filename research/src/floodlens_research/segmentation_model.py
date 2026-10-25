"""Compact, three-scale U-Net used only by the research pipeline."""

from __future__ import annotations

import torch
from torch import nn


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, inputs):
        return self.layers(inputs)


class FloodUNet(nn.Module):
    def __init__(self, in_channels: int = 2, base_channels: int = 8) -> None:
        super().__init__()
        widths = [base_channels, base_channels * 2, base_channels * 4]
        self.encoders = nn.ModuleList(
            [
                ConvBlock(in_channels, widths[0]),
                ConvBlock(widths[0], widths[1]),
                ConvBlock(widths[1], widths[2]),
            ]
        )
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = ConvBlock(widths[2], widths[2] * 2)
        self.upconvs = nn.ModuleList(
            [
                nn.ConvTranspose2d(widths[2] * 2, widths[2], 2, stride=2),
                nn.ConvTranspose2d(widths[2], widths[1], 2, stride=2),
                nn.ConvTranspose2d(widths[1], widths[0], 2, stride=2),
            ]
        )
        self.decoders = nn.ModuleList(
            [
                ConvBlock(widths[2] * 2, widths[2]),
                ConvBlock(widths[1] * 2, widths[1]),
                ConvBlock(widths[0] * 2, widths[0]),
            ]
        )
        self.output = nn.Conv2d(widths[0], 1, 1)

    def forward(self, inputs):
        skips = []
        values = inputs
        for encoder in self.encoders:
            values = encoder(values)
            skips.append(values)
            values = self.pool(values)
        values = self.bottleneck(values)
        for upconv, decoder, skip in zip(self.upconvs, self.decoders, reversed(skips)):
            values = upconv(values)
            values = decoder(torch.cat((skip, values), dim=1))
        return self.output(values)
