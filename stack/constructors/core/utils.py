from aws_cdk.aws_autoscaling import (
    EbsDeviceVolumeType,
    BlockDevice,
    BlockDeviceVolume,
)


def block_device(
    volume_type=EbsDeviceVolumeType.STANDARD, volume_size: int = 30
):
    return BlockDevice(
        device_name="/dev/xvda",
        volume=BlockDeviceVolume.ebs(
            volume_size=volume_size,  # >= 30
            volume_type=volume_type,
        ),
    )


def _90_percent(target: int) -> int:
    """useful to set a hard limit to the 90%, available memory often is
    100mb less of what is expected, if your instance type has not enough
    memory it won't be ran (even if 100mb)"""
    return target - (target // 10)


def _75_percent(target: int) -> int:
    """useful to set a soft limit to the 75%"""
    return target - (target // 4)
