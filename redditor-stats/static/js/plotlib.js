// Data visualizing functions collection
// Rasmus Heikkilä, 2015

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


// Function for drawing a line/area graph from post scores.
function postplot(posts) {
	
	var graph = d3.select("#postplot"),
		margin = {top: 20, right: 30, left: 40, bottom: 40},
		width = 880 - margin.right - margin.left,
		height = 500 - margin.top - margin.bottom;
		
	var num = "score";
	
	// Get domain for x-axis
	var xDomain = []
	for (i in posts) {
		xDomain.push(posts[i]["data"]["created_utc"]);
	}
		
	var x = d3.scale.ordinal()
			.rangePoints([0, width])
			.domain(xDomain);
			
	var extent = d3.extent(posts, (function(d) { return d.data[num]; }));
			
	var y = d3.scale.linear()
			.range([height, 0])
			.domain(extent);
			
	var xAxis = d3.svg.axis()
			.scale(x)
			.orient("bottom");
			
	var yAxis = d3.svg.axis()
			.scale(y)
			.orient("left");
			
	var area = d3.svg.area()
			.x(function(d) { return x(d.data.created_utc); })
			.y0(height)
			.y1(function(d) { return y(d.data[num]); })
			.interpolate("monotone");

	var line = d3.svg.line()
			.x(function(d,i) { return x(d.data.created_utc); })
			.y(function(d) { return y(d.data[num]); })
			.interpolate("monotone");
			
	var svg = graph.append("svg")
			.attr("width", width + margin.left + margin.right)
			.attr("height", height + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
			
	var tooltip = d3.tip()
				.attr("class", "d3-tip")
				.offset([-10, 0])
				.html(function(d) {return parseHTML(d); });
					
	svg.call(tooltip);
	
	function parseHTML(d) {
		return '<a href= "' + getLink(d) + '" target="_blank">' + 
				d.data.created_utc +
				"</a>" + 
				"<br> Score: " + d.data[num];				
	}
	
	function getLink(e) {
		if (e.kind == "t3") {
			return e.data.url;
		} else {
			return "http://www.reddit.com/comments/" + e.data.link_id.slice(3) + "/_/" + e.data.id;
		}
	}
			
	svg.append("g")
		.attr("class", "x axis")
		.attr("transform", "translate(0," + height + ")")
		.call(xAxis)
	  .selectAll("text")
		.attr("x", 8)
		.attr("y", 10)
		.attr("dy", ".70em")
		.attr("transform", "rotate(-40)")
		.style("text-anchor", "end");
		
	svg.append("g")
		.attr("class", "y axis")
		.call(yAxis)
	  .append("text")
		.attr("transform", "rotate(-90)")
		.attr("y", 6)
		.attr("dy", ".71em")
		.style("text-anchor", "end")
		.text("Score");
		
	svg.append("path")
		.datum(posts)
		.attr("class", "area")
		.attr("d", area);
		
	svg.append("path")
		.datum(posts)
		.attr("class", "line")
		.attr("d", line);
	
	svg.selectAll(".dot")
		.data(posts)
	  .enter().append("circle")
		.attr("class", "dot")
		.attr("cx", line.x())
		.attr("cy", line.y())
		.attr("r", 3)
		.on("mouseover", function(d) {
		  tooltip.show(d);
		})
		.on("mouseout", function(d) {
			d3.selectAll(".d3-tip").transition()
			.delay(1500)
			.duration(200)
			.style("opacity", 0)
			.style("pointer-events", "none");
		});
}


// Plots wordcloud
function wordcloud(data) {
	
	var color = d3.scale.category20(),
		width = 880,
		height = 450;
		
	var minmax = d3.extent(data, function(d) {return d.count; });
	var s = d3.scale.log().domain(minmax).range([5, 150]);
	
	
	var cloud =	d3.layout.cloud().size([width, height])
			.words(data.map(function(d) {
				return {text: d.word, size: s(d.count*1.25)};
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