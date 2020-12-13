$(document).ready(function () {
    var canvas = document.getElementById('canvas');
    var img = null;
    var image_id = null;

    // load an undescribed image
    function loadNewImage() {
        canvas.innerHTML = 'Loading new image...';
        $.ajax({
            type: 'GET',
            url: 'images',
            accepts: 'application/json',
        }).done(function (images) {
            console.log(images);
            var new_image_id = images[0].id;
            for (var imageNumber in images) {
                var image = images[imageNumber];
                if (image.id > image_id) {
                    new_image_id = image.id;
                    break;
                }
            }
            image_id = new_image_id;
            console.log('New image ID=' + image_id)
            img = document.createElement('img');
            img.src = 'image?id=' + image_id;

            canvas.innerHTML = '';
            canvas.appendChild(img);
            // load existing descriptions
            $.ajax({
                type: 'GET',
                url: 'images/' + image_id + '/descriptions',
                accepts: 'application/json',
            }).done(function (descriptions) {
                console.log(descriptions);
                for (descrNumber in descriptions) {
                    var d = descriptions[descrNumber];
                    var description = new Description(d.id, d.x, d.y);
                    description.extend(d.x + d.width, d.y + d.height);
                    description.markFinished();
                }
            })
        })
    }
    loadNewImage();

    function Description(descr_id, start_x, start_y) {
        this.id = descr_id;

        this.start_x = this.end_x = start_x;
        this.start_y = this.end_y = start_y;

        this.left = function () {
            return Math.min(this.start_x, this.end_x);
        }
        this.top = function () {
            return Math.min(this.start_y, this.end_y);
        }
        this.width = function () {
            return Math.abs(this.end_x - this.start_x);
        }
        this.height = function () {
            return Math.abs(this.end_y - this.start_y);
        }

        this.rectangle = document.createElement('div');
        this.rectangle.id = descr_id;
        this.rectangle.className = 'rectangle'
        canvas.appendChild(this.rectangle)

        this.extend = function (x, y) {
            this.end_x = x;
            this.end_y = y;
            this.rectangle.style.left = (img.offsetLeft + this.left()) + 'px';
            this.rectangle.style.top = (img.offsetTop + this.top()) + 'px';
            this.rectangle.style.width = this.width() + 'px';
            this.rectangle.style.height = this.height() + 'px';
        }

        this.markFinished = function () {
            this.rectangle.className += ' rectangle_ready';
        }
    }
    var description = null;

    var mouse = {
        x: 0,
        y: 0,
        setPosition: function (e) {
            var ev = e || window.event; //Moz || IE
            if (ev.pageX) { //Moz
                this.x = ev.pageX + window.pageXOffset;
                this.y = ev.pageY + window.pageYOffset;
            } else if (ev.clientX) { //IE
                this.x = ev.clientX + document.body.scrollLeft;
                this.y = ev.clientY + document.body.scrollTop;
            }
            this.x -= img.offsetLeft;
            this.y -= img.offsetTop;
        }
    }

    canvas.onmousemove = function (e) {
        mouse.setPosition(e);
        if (description !== null) {
            description.extend(mouse.x, mouse.y);
        }
    }

    canvas.onclick = function () {
        if (description !== null) {
            var finished_description = description;
            $.ajax({
                type: 'POST',
                url: 'images/' + image_id + '/descriptions/' + description.id,
                accepts: 'application/json',
                dataType: 'json',
                data: {
                    'x': description.left(),
                    'y': description.top(),
                    'width': description.width(),
                    'height': description.height(),
                }
            }).done(function (data) {
                finished_description.markFinished();
            })
            description = null;
            canvas.style.cursor = "default";
        } else {
            var descr_id = canvas.childElementCount - 1;
            description = new Description(descr_id, mouse.x, mouse.y);
            canvas.style.cursor = "crosshair";
        }
    }

    document.getElementById('clear').onclick = function () {
        var confirmation = confirm("Czy na pewno chcesz usunąć wszystkie opisy obrazu?");
        if (confirmation) {
            $.ajax({
                type: 'DELETE',
                url: 'images/' + image_id + '/descriptions',
                accepts: 'application/json',
            }).done(function (data) {
                var child = canvas.firstChild;
                while (child !== null) {
                    var nextSibling = child.nextSibling;
                    if (child.tagName === 'DIV')
                        child.remove();
                    child = nextSibling;
                }
            })
        }
    }

    document.getElementById('undo').onclick = function () {
        var last_child = canvas.childNodes[canvas.childNodes.length - 1];
        console.log(last_child);
        if (last_child.tagName === 'DIV') {
            $.ajax({
                type: 'DELETE',
                url: 'images/' + image_id + '/descriptions/' + last_child.id,
                accepts: 'application/json',
            }).done(function (data) {
                last_child.remove();
            })
        }
    }

    document.getElementById('save').onclick = function () {
        $.ajax({
            type: 'PUT',
            url: 'images/' + image_id,
            accepts: 'application/json',
        }).done(function (data) {
            loadNewImage();
        })

    }

    document.getElementById('next').onclick = function () {
        loadNewImage();
    }

})
