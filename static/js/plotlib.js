// Data visualizing functions collection
// Rasmus Heikkilä, 2016

// Plots subreddit bar graph
function barplot(data) {
	
	var margin = {top: 20, right: 20, bottom: 80, left: 40},
		width = 880 - margin.right - margin.left,
		height = 500 - margin.top - margin.bottom
		graph = d3.select("#barplot");
		
	var num = "count"
	
	var max = d3.max(data, function(d) {return d.data[num]});
	
	function getXDomain() {
		return data.sort(function(a,b) {return b.data[num] - a.data[num]; }).map(function(d) {return d.name; });
	}
		
	var x = d3.scale.ordinal()
			.rangeRoundBands([0, width], 0.1)
			.domain(getXDomain());
			
	var y = d3.scale.linear()
			.range([height, 0])
			.domain([0, max]);
	
	var xAxis = d3.svg.axis()
			.scale(x)
			.orient("bottom");
	
	var yAxis = d3.svg.axis()
			.scale(y)
			.orient("left");
			
	var svg = graph.append("svg")
			.attr("width", width + margin.left + margin.right)
			.attr("height", height + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
			
	var tooltip = d3.tip().attr("class", "d3-tip").offset([-10, 0]).html( function(d) {
		return "<strong>/r/" + d.name + "</strong><br>" + "Value: " + d.data[num];
	});
	svg.call(tooltip);
			
	svg.append("g")
		.attr("class", "x axis")
		.attr("transform", "translate(0," + height + ")")
		.call(xAxis)
	  .selectAll("text")
		.attr("dy", ".70em")
		.attr("y", 10)
		.attr("transform", "rotate(-40)")
		.style("text-anchor", "end");
		
	svg.append("g")
		.attr("class", "y axis")
		.call(yAxis)
		
	svg.selectAll(".bar")
		.data(data)
	  .enter().append("rect")
		.attr("class", "bar")
		.attr("x", function(d) {return x(d.name); })
		.attr("width", x.rangeBand())
		.attr("y", function(d) {return y(d.data[num]); })
		.attr("height", function(d) { return height - y(d.data[num]); })
		.on("mouseover", function(d) {
			tooltip.attr("class", "d3-tip animate").show(d)
		})
		.on("mouseout", function(d) {
			tooltip.attr("class", "d3-tip animate").show(d)
			tooltip.hide()
		});
		
	d3.select("#selector").on("change", function() {
		num = this.value
		
		y.domain([0, d3.max(data, function(d) {return d.data[num]})]);
		x.domain(getXDomain());
		
		var t0 = svg.transition().duration(500);
		t0.selectAll("rect")
			.attr("x", function(d) {return x(d.name); })
			.attr("y", function(d) {return y(d.data[num]); })
			.attr("height", function(d) { return height - y(d.data[num]); });
		t0.selectAll(".y.axis").call(yAxis);
		t0.selectAll(".x.axis").call(xAxis)
			.selectAll("text")
			.attr("y", 10)
			.style("text-anchor", "end");
		
	});

}


function addDays(date, days) {
    var dat = new Date(date);
    dat.setDate(date.getDate() + days);
    return dat; 
} // From: http://stackoverflow.com/questions/563406/add-days-to-datetime

// Recent activity graph inspired by Github commit chart
function activityPlot(posts) {
	
	var size = 90;
	var today = new Date(),
		start = addDays(today, -size);
		
	var calendar = [];
	var col = 0;
	
	for (i=0; i <= size; i++) {
		var date = addDays(start, i);
		
		// get day of week
		var c = date.getDay();
		
		// If sunday and we have already inserted a value, change column
		if (c===0 && i > 0) {
			col++;
		}
		
		// Initialize data element
		calendar.push({
			date: date,
			count: 0,
			col: col
		});
	}
	
	var margin = {top: 20, right: 30, left: 40, bottom: 40},
	    cellSize = 30,
		width = (cellSize * size / 7) + 2*cellSize;
		height = cellSize * 7;
	
	var dateFormat = d3.time.format("%d/%m/%y");
	
	var color = d3.scale.threshold()
				.domain([1, 5, 10, 50, 100, 500, 1000])
				.range(["white", "#eff3ff" , "#c6dbef", "#9ecae1", 
						"#6baed6", "#4292c6", "#2171b5" , "#084594"]);
				
				
	var svg = d3.select("#activityplot").append("svg")
			  .attr("width", width + margin.left + margin.right)
			  .attr("height", height + margin.top + margin.bottom)
			.append("g")
			  .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
			  
	var tooltip = d3.tip().attr("class", "d3-tip").offset([-10, 0]).html( function(d) {
		return "<strong>" + dateFormat(d.date) + "</strong><br>" + "Karma: " + d.count;
	});
	svg.call(tooltip);
			  
	
	// Get post scores for each day
	var scoresPerDay = {}
	var postCount = posts.length;
	for (i=0; i < postCount; i++) {
		var postDate = posts[i].data.created_utc;
		if (!scoresPerDay[postDate]) {
			scoresPerDay[postDate] = 0;
		}
		scoresPerDay[postDate] += posts[i].data.score;
	}
	
	// Match gathered scores with graph elements
	for (i=0; i <= size; i++) {
		if (scoresPerDay[dateFormat(calendar[i].date)]){
			calendar[i].count = scoresPerDay[dateFormat(calendar[i].date)];
		}
	}
	
	// Prepare the graph
	svg.selectAll(".day")
		.data(calendar)
		.enter()
	  .append("rect")
		.attr("class","day")
		.attr("width", cellSize)
		.attr("height", cellSize)
		.attr("x", function(d,i) { return d.col * cellSize;})
		.attr("y", function(d,i) { return d.date.getDay() * cellSize;})
		.attr("fill", function(d,i) { return color(d.count);})
		.on("mouseover", function(d) {
			tooltip.attr("class", "d3-tip animate").show(d)
		})
		.on("mouseout", function(d) {
			tooltip.attr("class", "d3-tip animate").show(d)
			tooltip.hide()
		});
		
	svg.append('text')
		.text('M')
		.style('fill','#ccc')
		.attr('text-anchor','middle')
		.attr('dx','-20')
		.attr('dy', cellSize + margin.top);

	svg.append('text')
		.text('W')
		.style('fill','#ccc')
		.attr('text-anchor','middle')
		.attr('dx','-20')
		.attr('dy', 3 * cellSize + margin.top);

	svg.append('text')
	    .text('F')
	    .attr('text-anchor','middle')
	    .style('fill','#ccc')
	    .attr('dx','-20')
	    .attr('dy', 5 * cellSize + margin.top);
	
}


function radarchart(daydata, hourdata) {

	// Hours are in UTC, change them to the client's time zone
	var parseDate = d3.time.format("%H:%M");
	var hrs = -(new Date().getTimezoneOffset() / 60);
	for (i=0, len = hourdata[0].axes.length; i < len; i++) {
		var utchour = parseDate.parse(hourdata[0].axes[i].axis);
		utchour.setHours((utchour.getHours() + hrs)%24);
		hourdata[0].axes[i].axis = parseDate(utchour);
	}
	
	// Reverse the data because radar-chart plots it CCW
	hourdata[0].axes = hourdata[0].axes.reverse();
	daydata[0].axes = daydata[0].axes.reverse();

	var radarwidth = 350,
	radarheight = 350;
	var cfg = {
	w: radarwidth,
	h: radarheight,
	levels: 5,
	};

	var radar = RadarChart.chart();
	radar.config(cfg);
	var svg = d3.select("#radar").append("svg")
	.attr("width", cfg.w * 2 + 150)
	.attr("height", cfg.h * 1.25);

	function render() {
	var plot = svg.selectAll("g.plot").data([daydata, hourdata]);
	plot.enter().append('g').classed('plot', 1);
	plot.attr("transform", function(d,i) {return "translate(" + (20 + (i * (100 + cfg.w))) + "," + 20 + ")"; })
	.call(radar);
	}
	render();
}

// Plots wordcloud
function wordcloud(data) {
	
	var color = d3.scale.category20(),
		width = 880,
		height = 450;
		
	var minmax = d3.extent(data, function(d) {return d.count; });
	var s = d3.scale.log().domain(minmax).range([16, 100]);
	
	
	var cloud =	d3.layout.cloud().size([width, height])
			.words(data.map(function(d) {
				return {text: d.word, size: s(d.count)};
			}))
			.padding(3)
			.rotate(function() {return ~~(Math.random() * 2) * 90; })
			.font("Helvetica")
			.fontSize(function(d) {return d.size; })
			.timeInterval(1)
			.on("end", draw);
	
	cloud.start();
		
	function draw(words) {
		d3.select("#cloud").append("svg")
			.attr("width", width)
			.attr("height", height)
		  .append("g")
		    .attr("transform", "translate(" + cloud.size()[0] / 2 + "," + cloud.size()[1] / 2 + ")")
		  .selectAll("text")
			.data(words)
		  .enter().append("text")
			.style("font-size", function(d) { return d.size + "px"; })
			.style("font", "Helvetica")
			.style("fill", function(d,i) { return color(i); })
			.attr("text-anchor", "middle")
			.attr("transform", function(d) {
				return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
			})
			.text(function(d) {return d.text; });
	}
}