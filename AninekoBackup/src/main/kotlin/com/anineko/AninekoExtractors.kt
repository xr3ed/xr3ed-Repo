package com.anineko

import com.lagradost.cloudstream3.extractors.StreamWishExtractor
import com.lagradost.cloudstream3.extractors.DoodLaExtractor

class StreamwishHG : StreamWishExtractor() {
    override var mainUrl = "https://otakuhg.site"
    override var name = "Streamwish [Backup]"
}

class Playmogo : DoodLaExtractor() {
    override var mainUrl = "https://playmogo.com"
    override var name = "Doodstream [Backup]"
}

class VibePlayer : StreamWishExtractor() {
    override var mainUrl = "https://vibeplayer.site"
    override var name = "HD-1 [Backup]"
}

class Bibiemb : StreamWishExtractor() {
    override var mainUrl = "https://bibiemb.xyz"
    override var name = "HD-2 [Backup]"
}

class Earnvids : StreamWishExtractor() {
    override var mainUrl = "https://otakuvid.online"
    override var name = "Earnvids [Backup]"
}
