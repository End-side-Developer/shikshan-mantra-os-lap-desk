import QtQuick 2.5;
import calamares.slideshow 1.0;
Presentation {
    id: presentation
    Slide {
        Image { source: "slide1.svg"; anchors.horizontalCenter: parent.horizontalCenter }
        Text { text: "Welcome to Shikshan Mantra OS"; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; font.pixelSize: 22 }
    }
    Timer { interval: 10000; running: true; repeat: true; onTriggered: presentation.goToNextSlide() }
}
