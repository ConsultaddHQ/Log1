import os

if os.getenv('ENV') == 'prod':
    LEGAL = "legal@consultadd.com"
    FINANCE = "finance@consultadd.com"
    RELATIONS = "relations@consultadd.com"
    RECRUITMENT = "recruitment@consultadd.com"
    ENGINEERING = "engineering@consultadd.com"
    SUPERADMIN = ["sudeep.b@consultadd.com"]

    # Discord Webhooks
    # Announcement Channel
    announcement_url = 'https://discordapp.com/api/webhooks/538357619190923265/2JLKDwILDNqLj7YlmGS-ZuQxx26r4JRK91TvE8cHMtLZbvCdUoHyXLZ20uuaGmFPE5fF'
    # Offer Announcement Channel
    offer_url = "https://discordapp.com/api/webhooks/541981508815028224/21xjw0j7AE3bfmcqJ7B-b19sFKzO5eIwpSXe8OTVtoRK65XQIy5FhN3LhJ1ktE1Wsth6"
    # Recruitment Channel
    recruitment_url = "https://discordapp.com/api/webhooks/626004000273072128/QH309Z7YfNr7ER9aFeWDpRJX_1eAR2soVzzkBaVAq7CWfOV3Nuzyz9n-IhnVrjuEAwX3"
    # 45 days limit Channel
    pool_channel_url = "https://discordapp.com/api/webhooks/626001183076778004/KzKrcylbIantpPtFKLmNTGxILSTYBn4Q07MyDTLYbzB0Tj8m1JrMFBe97NJVTWKuXd_5"

elif os.getenv('ENV') == 'local' or os.getenv('ENV') == 'dev':
    LEGAL = "sarang.m@consultadd.in"
    FINANCE = "sarang.m@consultadd.in"
    RELATIONS = "sarang.m@consultadd.in"
    RECRUITMENT = "sarang.m@consultadd.in"
    ENGINEERING = "sarang.m@consultadd.in"
    SUPERADMIN = ["sarang.m@consultadd.in"]

    # Discord Webhooks
    announcement_url = 'https://discordapp.com/api/webhooks/598067483563261964/AQS6JZRlrVO2XXzewZLyQewav49gxjkHJ7ENUi8mMFDfeVUSBV9aieVHeFsEazIEiYLw'
    offer_url = 'https://discordapp.com/api/webhooks/598067483563261964/AQS6JZRlrVO2XXzewZLyQewav49gxjkHJ7ENUi8mMFDfeVUSBV9aieVHeFsEazIEiYLw'
    recruitment_url = 'https://discordapp.com/api/webhooks/598067483563261964/AQS6JZRlrVO2XXzewZLyQewav49gxjkHJ7ENUi8mMFDfeVUSBV9aieVHeFsEazIEiYLw'
    pool_channel_url = 'https://discordapp.com/api/webhooks/598067483563261964/AQS6JZRlrVO2XXzewZLyQewav49gxjkHJ7ENUi8mMFDfeVUSBV9aieVHeFsEazIEiYLw'
